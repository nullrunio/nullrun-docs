---
title: Error handling
maturity: stable
description: How a NullRun refusal reaches your code, your monitoring and your users — three layers, one fail-closed contract, and the codes you will meet.
---

# Error handling

Errors in NullRun come in three layers, one for each audience: your
code, your monitoring, and your end user. The SDK ships all three.
You pick how much of each to use.

| Layer | Mechanism | Audience |
|---|---|---|
| 1. Structured exception | `except NullRunError` | Your code — retry, fail, or surface it |
| 2. `on_error` hook | `@nullrun.on_error` | Sentry, Datadog, your log aggregator |
| 3. `guard()` / `format_user_message` | `with nullrun.guard():` | The end user — one clean sentence |

## Layer 1 — the structured exception

Every NullRun exception carries four fields:

| Field | What it is | Example |
|---|---|---|
| `error_code` | Stable machine-readable identifier | `NR-B004` |
| `user_action` | What to do next | `Request a fresh approval row and retry /gate.` |
| `retryable` | Whether a backoff retry makes sense | `True` for a rate limit, `False` for a budget |
| `docs_url` | Link to the code's reference page | `https://docs.nullrun.io/errors` |

### The hierarchy

Every public exception inherits from `NullRunError`. Two marker classes
split it by kind of event:

| Marker | What it covers |
|---|---|
| `NullRunDecision` | The gate reached a verdict — budget cap, tool block, approval, chain rejection, workflow pause |
| `NullRunInfrastructureError` | The SDK could not reach or read the gateway — network, 5xx, auth, config |

One class sits outside both: `WorkflowKilledInterrupt`, the
control-plane kill signal. It inherits from `NullRunError` directly, so
`except NullRunDecision` does not catch it. Catch it by name.

The full tree, with every class and its code, is in
[Reference → Errors](../reference/errors.md#sdk-exception-hierarchy).

### Retry or not

`retryable` tells you whether a backoff retry is the right response.

| Retryable | Codes |
|---|---|
| `True` | `NR-B001`, `NR-B002`, `NR-R001`, `NR-R002`, `NR-P002`, `NR-P004`, `NR-A010`, `NR-B006`, `NR-A016`, `NR-MCP03` |
| `False` | Every other code |

The full catalog is in
[Reference → Errors](../reference/errors.md#nr-error-code-catalog).

### Catching

Branch on the exception type when the outcome differs. Otherwise catch
the parent and read `error_code`:

```python
import nullrun
from nullrun import NullRunError, NullRunBudgetError

@nullrun.protect
def my_agent(prompt):
    try:
        return call_llm(prompt)
    except NullRunBudgetError:
        return "I have reached my budget for this period."
    except NullRunError as exc:
        # exc.error_code, exc.retryable, exc.user_action, exc.docs_url
        raise
```

For a rate limit, the exception carries the wait the server asked for:

```python
from nullrun import RateLimitError

try:
    my_agent(prompt)
except RateLimitError as exc:
    # exc.retry_after is the number of seconds the server asked for.
    # exc.upgrade_url points at the plan upgrade page when the limit
    # is a plan limit.
    time.sleep(exc.retry_after)
```

## Layer 2 — the `on_error` hook

Register a hook and it fires for every `NullRunError` that
propagates:

```python
import nullrun
import sentry_sdk

@nullrun.on_error
def _to_sentry(err, ctx):
    sentry_sdk.capture_exception(err, extra={
        "code": err.error_code,
        "retryable": err.retryable,
        "stage": ctx.stage,
        "workflow_id": ctx.workflow_id,
        "tool_name": ctx.tool_name,
    })
```

The hook fires once per error, in registration order. A hook that
raises is caught and logged — a broken Sentry integration cannot break
your agent.

The context object carries:

| Field | Meaning |
|---|---|
| `stage` | Where the error fired: `init`, `auth`, `policy_fetch`, `execute`, `track`, `gate`, `check`, `sensitive_tool`, `org_status`, `ws`, `transport` |
| `workflow_id` | The active workflow, or `None` if the error fired with no workflow bound |
| `tool_name` | The tool that triggered the error, or `None` |
| `api_key_prefix` | A short non-secret fingerprint of the key in use |
| `correlation_id` | Per-request identifier |
| `timestamp` | When the error fired |
| `extra` | Free-form dict for stage-specific metadata |

**The kill signal fires the hook on the sync path only.** See
[Kill signal](#kill-signal).

Registering several hooks is fine. Each returns a callable that
unregisters it.

## Layer 3 — `guard()` and `format_user_message`

For a script that should print a friendly message and stop, wrap the
call:

```python
import nullrun

@nullrun.protect
def my_agent(prompt):
    return call_llm(prompt)


if __name__ == "__main__":
    with nullrun.guard():
        print(my_agent("What does NullRun do?"))
```

`guard()` catches every `NullRunError` raised inside the block,
prints one report to stderr, and exits with code 1. The report opens
with the user message, then gives the developer the code, the stage,
the endpoint, the cause, the fix, and a link:

```
Too many requests. Please wait a moment and try again.
  [NR-R001] what: /api/v1/gate (retryable)
           where: endpoint=/api/v1/gate status=429 source=GATEWAY_ERROR
           why: Transport error on /api/v1/gate: rate limit exceeded (source=GATEWAY_ERROR, details={'retry_after': 30.0})
           how to fix: The NullRun backend rate-limited this API key. Wait retry_after seconds (or upgrade the plan) before retrying.
           docs: https://docs.nullrun.io/errors
```

`guard()` accepts `exit_code` if you want a different status.

A non-NullRun exception propagates unchanged — your own bugs deserve an
honest traceback. The kill signal is the one NullRun exception with a
special rule, described in [Kill signal](#kill-signal).

### Branded wording

Override the user-facing sentence for one code at the top of your
entry point:

```python
import nullrun

nullrun.set_user_message(
    "NR-B004",
    "You've used all your support credits. Upgrade to keep chatting.",
)
```

Overrides live in a per-process dict. They do not persist across
processes and they are not synced to the gateway.

## Server frameworks

`guard()` exits the process, so it does not fit a request handler.
Catch the exception and map it to an HTTP status yourself:

```python
import nullrun
from nullrun import NullRunError

@app.post("/chat")
async def chat(req: ChatRequest):
    try:
        return await run_agent(req.message)
    except NullRunError as exc:
        raise HTTPException(
            status_code=getattr(exc, "status_code", None) or 503,
            detail={
                "message": nullrun.format_user_message(exc),
                "code": exc.error_code,
            },
        )
```

Only some exception classes carry `status_code`, so read it with
`getattr`. `format_user_message(exc)` always returns a non-empty string
that is safe to show an end user.

## Kill signal

The operator can kill a running workflow. The signal arrives as
`WorkflowKilledInterrupt`, or its typed alias
`NullRunWorkflowKilledError`. How it reaches your code depends on the
`@protect` flavour:

| Flavour | What reaches your code |
|---|---|
| async `@protect` | The raw `WorkflowKilledInterrupt` propagates. The `on_error` hook stays silent. |
| sync `@protect` | It arrives re-wrapped as `NullRunBlockedException` with `error_code = "NR-W002"`. The hook fires. |

So `except WorkflowKilledInterrupt:` catches the kill on the async path
only. On the sync path, catch `NullRunBlockedException` and read
`error_code`.

`guard()` follows the same split. On the async path it re-raises the
kill, so the kill reaches the top of the agent loop. On the sync path
the kill is already a `NullRunBlockedException`, so `guard()` prints
the report and exits with status 1.

To keep the process alive after a kill — checkpoint, notify a
supervisor, then exit — use a bare `@protect` with your own
`except NullRunBlockedException:` arm and check `error_code == "NR-W002"`.

## Fail closed

Every check on the enforcement path **refuses** when it cannot be
evaluated. A refusal is a refusal, not a pass. The body of a
protected function does not run on a refused call.

| Situation | Result |
|---|---|
| The gateway cannot be reached | The body does not run. A network failure raises `NullRunTransportError` (`NR-B001`) and a gateway 5xx raises `NullRunBackendError` (`NR-B002`); `@protect` re-raises both as `NullRunBlockedException` with the same code. A rejected key raises `NullRunAuthError` with `NR-A003`. |
| The rate-limit store cannot be reached | HTTP 503 `RATE_LIMIT_REDIS_UNAVAILABLE` |
| The budget store cannot be reached | HTTP 402 `BUDGET_REDIS_UNAVAILABLE` |
| A `ToolBlock` policy cannot be evaluated | HTTP 403 `TOOL_BLOCKED` |
| The approval window closes with no decision | `NullRunApprovalExpiredError` (`NR-A012`) |

The SDK circuit breaker is the one local exception. After repeated
transport failures it stops the event flush and keeps the pending events
on disk. It never lets a protected call through unchecked. See
[Circuit breaker](circuit-breaker.md).

## Audit trail

Gate decisions land in **Governance → Audit log**. Each row carries the
decision, the reason code, the matched rule, the policy, the execution
id and the tool name. It answers "why did my agent stop working at
14:32?".

The log is hash-chained: each row carries the hash of the row before
it. `GET /api/v1/orgs/{org_id}/audit-log/verify` recomputes the chain
and names the first row that does not match.

The **Audit log** page needs the plan's audit log feature. Lite and
Starter do not include it, so those plans record no gate decisions.
Pair it with [Traces](tracing.md) for the request behind the decision.

## What is NOT stored

NullRun never persists:

- **Prompt content** or **LLM response payloads**. The gate receives
  only the model name, the tool name, the tool list, an estimated
  token count and an optional typed `business_impact` payload.
- **Card numbers, CVC, expiry month or year.** Subscriptions carry
  only the payment method brand and its last four digits.
- **OAuth refresh tokens.** The identity provider owns session
  lifetime.

Tool arguments are the one case worth naming. The SDK ships the
argument bag so the gate can evaluate a `tool_parameters` approval
predicate and bind the approval digest to those exact arguments. The
control center renders the tool name and the argument count, not the
values.

Personal data is redacted at the log boundary: email addresses, phone
numbers, card numbers and tokens are replaced with a marker before the
row is written. Uppercase `KEY=VALUE` pairs are rewritten to
`KEY=[REDACTED]` before the bytes reach stdout.

## See also

- [Reference → Errors](../reference/errors.md) — the full catalog
- [Troubleshooting](../troubleshooting.md) — common failures and fixes
- [Use with FastAPI](../how-to/fastapi.md) — exception handling in
  ASGI handlers
- [Tracing](tracing.md) — how errors map to spans
