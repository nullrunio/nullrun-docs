---
title: Error handling
maturity: stable
description: The NullRun exception hierarchy, the three layers of error handling, and the fail-CLOSED contract on the enforcement path.
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
| `user_action` | What to do next | `Wait 30s, then retry the call.` |
| `retryable` | Whether a backoff retry makes sense | `True` for a rate limit, `False` for a budget |
| `docs_url` | Link to the code's reference page | `https://docs.nullrun.io/reference/errors` |

### The hierarchy

```
Exception
└── BreakerError
    └── NullRunError
        ├── NullRunDecision          a policy outcome: block, pause, approval
        │   ├── NullRunBlockedException        generic block (NR-X001)
        │   │   ├── NullRunBudgetError         (NR-B004)
        │   │   │   └── NullRunBudgetRecheckFailedError (NR-B006)
        │   │   ├── NullRunToolBlockedError    (NR-T001)
        │   │   ├── NullRunDeniedError         (NR-D001)
        │   │   ├── NullRunApprovalNotYetApprovedError (NR-A010)
        │   │   ├── NullRunApprovalDeniedError (NR-A011)
        │   │   ├── NullRunApprovalExpiredError (NR-A012)
        │   │   ├── NullRunApprovalReplayRejectedError (NR-A015)
        │   │   ├── NullRunApprovalDigestMismatchError (NR-A013)
        │   │   ├── NullRunApprovalToolDigestMismatchError (NR-A014)
        │   │   └── NullRunApprovalToolMismatchError (NR-A017)
        │   ├── NullRunConsumeOverbudgetError   (NR-O001)
        │   ├── NullRunChainError               (NR-CH001)
        │   ├── NullRunWorkflowInactiveError    (NR-W004)
        │   └── WorkflowPausedException         (NR-W003)
        ├── NullRunInfrastructureError  a dependency could not be reached
        │   ├── NullRunTransportError   (NR-B001)
        │   │   ├── NullRunBackendError (NR-B002)
        │   │   └── RateLimitError      (NR-R001)
        │   ├── NullRunProtocolError    (NR-P001)
        │   ├── NullRunGateIndeterminateError (NR-P004)
        │   ├── NullRunRateLimitRedisError (NR-R002)
        │   ├── NullRunConfigError      (NR-C000)
        │   └── NullRunAuthenticationError (NR-A001)
        │       └── NullRunAuthError    (NR-A003)
        └── WorkflowKilledInterrupt    the operator killed the workflow
            └── NullRunWorkflowKilledError
```

Two things to internalise:

- **`WorkflowKilledInterrupt` is not a `NullRunDecision`.** It sits
  directly under `NullRunError`. Catch it by name.
- **`NullRunApprovalDeniedError` and `NullRunApprovalExpiredError`
  are siblings**, not the same class. One is a decision, the other is
  a timeout.

### Codes you will meet

| Code | Meaning | Retryable |
|---|---|---|
| `NR-B001` | The gateway could not be reached (network) | Yes |
| `NR-B002` | The gateway returned a server error | Yes |
| `NR-B004` | The workflow budget for this period is exhausted | No |
| `NR-B005` | The SDK circuit breaker is open | Yes |
| `NR-B006` | The post-approval budget re-check failed | No |
| `NR-R001` | The rate limit for this workflow or key is exhausted | Yes |
| `NR-R002` | The rate-limit store is unreachable | Yes |
| `NR-T001` | A ToolBlock pattern matched the tool name | No |
| `NR-CH001` | The chain context is unknown or does not belong to this org | No |
| `NR-O001` | The actual cost exceeded the reservation plus epsilon | No |
| `NR-W002` | The workflow was killed by the operator | No |
| `NR-W003` | The workflow is paused | Yes |
| `NR-W004` | The workflow was deleted or disabled | No |
| `NR-A001` | The SDK could not authenticate | No |
| `NR-A003` | The API key was rejected | No |
| `NR-A010` | The approval is still pending — nobody has decided | Yes |
| `NR-A011` | The operator denied the approval | No |
| `NR-A012` | The approval expired with no decision | Yes |
| `NR-A013` | The approved action differs from the request | No |
| `NR-A014` | The approved tool set differs | No |
| `NR-A015` | The approval grant was already consumed | No |
| `NR-P001` | The SDK and the gateway speak different protocol versions | No |
| `NR-X001` | A block with no dedicated exception class | Depends |

The full catalog is in [Reference → Errors](../reference/errors.md).

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

**The kill signal does not fire the hook.** A kill is a control-plane
action, not an SDK failure. See [Kill signal](#kill-signal).

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
prints a developer report to stderr, and exits with code 1. The report
has the catalog headline plus the code, the endpoint, the cause, and
the fix:

```
Too many requests. Please wait a moment and try again.
  [NR-R001] what: gate (retryable)
           where: endpoint=/api/v1/gate status=429 source=GATEWAY_ERROR
           why: Per-workflow rate limit exceeded; retry after 30s.
           how to fix: Wait 30s, then retry the call.
```

`guard()` accepts `exit_code` if you want a different status.

**One exception propagates unchanged: the kill signal.** `guard()`
re-raises `WorkflowKilledInterrupt` so a kill reaches the top of the
agent loop instead of turning into a graceful exit. A non-NullRun
exception also propagates — your own bugs deserve an honest
traceback.

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
            status_code=exc.status_code or 503,
            detail={
                "message": nullrun.format_user_message(exc),
                "code": exc.error_code,
            },
        )
```

`format_user_message(exc)` always returns a non-empty string that is
safe to show an end user.

## Kill signal

The operator can kill a running workflow. The signal arrives as
`WorkflowKilledInterrupt`, or its typed alias
`NullRunWorkflowKilledError`. Catch it by name when you need
kill-specific handling:

```python
from nullrun import NullRunError, NullRunWorkflowKilledError

try:
    my_agent(prompt)
except NullRunWorkflowKilledError:
    persist_state()
    raise
except NullRunError:
    log.error("agent failed", exc_info=True)
```

A kill is a control-plane action, so it behaves differently on the two
`@protect` flavours:

| Flavour | What reaches your code |
|---|---|
| async `@protect` | The raw `WorkflowKilledInterrupt` propagates. The `on_error` hook stays silent. |
| sync `@protect` | It arrives re-wrapped as `NullRunBlockedException` with `error_code = "NR-W002"`. The hook fires. |

`guard()` re-raises the kill either way, so a kill never turns into a
graceful exit. To keep the process alive after a kill — checkpoint,
notify a supervisor, then exit — use a bare `@protect` with your own
`except NullRunWorkflowKilledError:` arm.

## Fail closed

Every check on the enforcement path **refuses** when it cannot be
evaluated. A refusal is a refusal, not a pass. The body of a
protected function does not run on a refused call.

| Situation | Result |
|---|---|
| The gateway cannot be reached | The body does not run. `NullRunBlockedException` with a transport code: `NR-B001` network, `NR-B002` gateway 5xx, `NR-A003` auth, `NR-B005` breaker open |
| The rate-limit store cannot be reached | HTTP 503 `RATE_LIMIT_REDIS_UNAVAILABLE` |
| The budget store cannot be reached | HTTP 402 `BUDGET_REDIS_UNAVAILABLE` |
| A `ToolBlock` policy cannot be evaluated | HTTP 403 `TOOL_BLOCKED` |
| The approval window closes with no decision | `NullRunApprovalExpiredError` (`NR-A012`) |

The SDK circuit breaker is the one local exception. After repeated
transport failures it stops calling the gateway and keeps the pending
work on disk. See [Circuit breaker](circuit-breaker.md).

## Audit trail

Every gate decision lands in **Governance → Audit log**. Each row
carries the decision, the reason code, the matched rule, the policy,
the execution id and the tool name. It answers "why did my agent stop
working at 14:32?".

The **Audit log** page needs the plan's Audit log feature. A plan
without it does not record gate decisions.

Pair it with [Traces](tracing.md) for the request behind the decision.

## What is NOT stored

NullRun never persists:

- **Prompt content** or **LLM response payloads**. The gate receives
  only the model name, the tool name, the tool list, an estimated
  token count and an optional typed `business_impact` payload.
- **Tool arguments** beyond the typed `business_impact` extraction.
  Operators do not write JSONPath rules over tool payloads.
- **MCP interaction payloads** — only the canonical tool name is
  logged.
- **Card numbers, CVC, expiry month or year.** Subscriptions carry
  only the payment method brand and its last four digits.
- **OAuth refresh tokens.** The identity provider owns session
  lifetime.

Email addresses and prompts are hashed or redacted at the log and
trace-span boundary, so plaintext does not reach the structured log
store. Uppercase `KEY=VALUE` pairs are rewritten to `KEY=[REDACTED]`
so plaintext never reaches stdout.

## See also

- [Reference → Errors](../reference/errors.md) — the full catalog
- [Troubleshooting](../troubleshooting.md) — common failures and fixes
- [Use with FastAPI](../how-to/fastapi.md) — exception handling in
  ASGI handlers
- [Tracing](tracing.md) — how errors map to spans
