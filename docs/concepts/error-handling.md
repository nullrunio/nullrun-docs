title: Error handling
maturity: stable
description: The full NullRun exception hierarchy, kill-signal semantics, and the multi-layer fail-CLOSED contract that protects production traffic.
# Error handling

Errors in NullRun come in three layers, designed for three audiences:
your code, your monitoring, and your end users. The SDK does most of
the work — you pick how much of each layer to use.

## Where errors appear in the dashboard

Every error the SDK raises lands in **Governance → Decision History**
and **Governance → Audit log**:

- **Decision History** — the most recent N decisions per workflow,
  with the reason (`BUDGET_HARD_BLOCKED`, `TOOL_BLOCKED`,
  `RATE_LIMIT_EXCEEDED`, etc.). Useful for "what just happened?"
- **Audit log** — every decision ever, hash-chained and
  filterable by workflow, time range, decision type, tool name.
  Useful for compliance review and incident forensics.

<figure class="nr-shot">
  <img class="nr-shot__light" src="../../assets/images/screenshots/audit-log-light.png"
       alt="Audit log page listing every gate decision ever made by the org.">
  <img class="nr-shot__dark" src="../../assets/images/screenshots/audit-log-dark.png"
       alt="Audit log page listing every gate decision ever made by the org.">
  <figcaption class="nr-shot__caption">Governance · Audit log</figcaption>
</figure>

The audit log is the source of truth for "did the agent call the
right thing?". Pair it with [Traces](tracing.md) for full context.

## The three layers

| Layer | Who consumes it | What they see | Purpose |
|---|---|---|---|
| **1. Structured exception** | Your Python code | Exception type, error code, what to do next | Your code decides: retry, fail, surface to UI |
| **2. `on_error` hook** | Sentry / Datadog / logs | Same exception + context (workflow, tool, stage) | Observability: you see every error in your existing dashboards |
| **3. `@guarded` / `format_user_message`** | End user | One friendly sentence from a catalog | The user gets a clean message, not a stack trace |

The SDK ships all three. You decide how much to use.

## Layer 1 — the structured exception

Every NullRun exception carries four fields your code can branch on:

| Field | What it is | Example |
|---|---|---|
| `error_code` | Stable machine-readable identifier | `NR-B004`, `NR-R001`, `NR-T001` |
| `user_action` | What to do next | `Wait 30s, then retry` |
| `retryable` | True if retry-after-backoff makes sense | True for rate limit, False for budget |
| `docs_url` | URL to the per-code docs page | `https://docs.nullrun.io/reference/errors#sdk-exception-hierarchy-python` |

The full catalog lives in that reference page; the standard set is:

- `NR-B004` — workflow budget exhausted
- `NR-B002` — gateway 5xx
- `NR-B006` — post-approval budget re-check failed on the same envelope as the original `/gate`. The SDK raises `NullRunBudgetRecheckFailedError`. Operator must re-approve or the workflow can no longer run.
- `NR-R001` — per-workflow rate limit
- `NR-R002` — rate-limit Redis unavailable
- `NR-T001` — tool block list hit
- `NR-CH001` — chain context invalid
- `NR-W004` — workflow soft-deleted or killed
- `NR-A003` — API key rejected
- `NR-A010` — approval row exists, status `PENDING` — operator has not decided yet
- `NR-A011` — operator explicitly denied the approval — terminal, request a fresh grant
- `NR-A012` — approval expired (`expires_at` is in the past)
- `NR-A013` — business-impact digest drifted since operator approval — re-approval required
- `NR-A014` — capability digest drifted (silent capability-gain attack surface) — re-approval required
- `NR-A015` — grant already consumed by a prior `/execute` (replay rejected)
- `NR-P001` — wire-protocol version mismatch
- `NR-O001` — actual cost > reservation + ε (HTTP 422)
- `NR-X001` — generic catch-all raised when a policy block matches a code the SDK does not have a dedicated class for. Match on `NullRunBlockedException` and read `.error_code` if you want specific handling.

For the exception classes used to surface these codes, see
[Reference → Errors → SDK exception hierarchy](../reference/errors.md#sdk-exception-hierarchy-python).

The wire code is still available via the response body or `.status_code`
when you need it for metrics / dashboards.

You catch a specific exception type and inspect the fields:

```python
from nullrun.breaker.exceptions import RateLimitError

@nullrun.protect
def my_agent(prompt):
    try:
        return call_llm(prompt)
    except RateLimitError as exc:
        # exc.error_code = "NR-R001"
        # exc.retryable = True
        # exc.retry_after = 30  (seconds)
        # exc.upgrade_url = "..."  (link to upgrade plan)
        time.sleep(exc.retry_after)
        return call_llm(prompt)
```

For most cases you don't need to import specific types — catching
the parent `NullRunError` and reading `error_code` is enough.

## Layer 2 — the `on_error` hook

For Sentry / Datadog / your log aggregator, register a hook that fires
for every `NullRunError` **before** it propagates:

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

The hook fires **once per error**, in registration order. Hook
exceptions are caught and logged at DEBUG — a misbehaving Sentry
can't break your agent.

The context object (`ctx`) carries: `stage` (init / transport /
track / gate), `workflow_id`, `tool_name`, `api_key_prefix` (first
12 chars of the API key, never the full value), `correlation_id`
(per-request UUID), `timestamp`, `extra` (vendor-specific dict).

Multiple hooks are supported:

```python
@nullrun.on_error
def _to_sentry(err, ctx): ...

@nullrun.on_error
def _to_log(err, ctx):
    log.warning("NullRun error", extra={"code": err.error_code})
```

The hook fires for every `NullRunError` subclass. It does **not**
fire for `WorkflowKilledInterrupt` (a `BaseException` — kill is a
signal, not an error).

## Layer 3 — `@guarded` and `format_user_message`

For scripts that just want "run the agent and print a friendly
message on failure", use the zero-boilerplate helpers:

```python
from nullrun import init_or_die, guarded, protect, shutdown

init_or_die()

@guarded
@protect
def my_agent(prompt):
    return call_llm(prompt)


if __name__ == "__main__":
    try:
        print(my_agent("What does NullRun do?"))
    finally:
        shutdown()
```

What your terminal looks like on a rate-limit hit:

```
$ python my_agent.py
Too many requests. Please wait a moment and try again.
$ echo $?
1
```

`@guarded` catches every `NullRunError`, prints the catalog wording
to stderr, and exits with code 1. `WorkflowKilledInterrupt` still
propagates — kill is final, even with `@guarded`.

`@guarded` is for scripts and one-shots. For long-running services
you want explicit handling — see [Server frameworks](#server-frameworks)
below.

### Branded wording

If you want your own error messages (e.g. "You've used all your
support credits" instead of the default wording), call
`set_user_message` once at startup:

```python
import nullrun

nullrun.set_user_message(
    "NR-B004",
    "You've used all your support credits. Upgrade to keep chatting.",
)
```

Overrides live in a per-process dict. They don't persist across
processes and aren't synced to the gateway — they're presentation
sugar on top of the catalog.

## Server frameworks

For FastAPI / aiohttp / Flask / Django, you don't want `@guarded`
(it's a CLI helper). Instead, catch the exception in your request
handler and return an appropriate HTTP status:

```python
from nullrun import NullRunError

@app.post("/chat")
async def chat(req: ChatRequest):
    try:
        return await run_agent(req.message)
    except NullRunError as exc:
        # Return the catalog wording as the user-facing message,
        # log the structured fields server-side.
        raise HTTPException(
            status_code=exc.status_code or 503,
            detail={"message": nullrun.format_user_message(exc), "code": exc.error_code}
        )
```

The mapping from exception to HTTP status is documented in
[Reference → Errors → Decision subclasses to HTTP](../reference/errors.md#mapping-decision-subclasses-to-http).

## Audit trail

Every decision is recorded in the audit log; you can fetch the full
log via the API. The audit log is the source of truth for "did the
agent call the right thing?". Pair it with [Traces](tracing.md) for
full context.

## What is NOT stored

NullRun never persists:

- **Prompt content** or **LLM response payloads**. The gate
  receives only `model`, `tool`, `tools`, `estimated_tokens`, and
  optional `business_impact` typed payload.
- **Tool arguments** beyond the typed `BusinessImpact` extraction.
  Operators do not write JSONPath rules over tool payloads.
- **MCP interaction payloads** — only the canonical tool name is
  logged.
- **Card numbers, CVC, expiry month/year** — Polar is the
  merchant of record. Subscriptions carry only `payment_method_brand`
  and `payment_method_last4`.
- **OAuth refresh tokens** — the IdP owns session lifetime.

Email addresses and prompts are hashed or redacted at the log and
trace-span boundary so plaintext does not reach the structured log
store. Uppercase `KEY=VALUE` pairs are rewritten to `KEY=[REDACTED]`
before bytes reach stdout.

## Kill signal — special case

`WorkflowKilledInterrupt` is a `BaseException`, not an `Exception`.
This is deliberate — kill signals must propagate even if your code
catches everything:

```python
try:
    my_agent(prompt)
except Exception:
    # Operator clicked Kill. Don't swallow this.
    pass
# WorkflowKilledInterrupt is NOT caught here.
```

If you want a clean shutdown on kill, catch `WorkflowKilledInterrupt`
**explicitly before** any `except Exception`:

```python
try:
    my_agent(prompt)
except WorkflowKilledInterrupt:
    persist_state()  # save checkpoint
    raise           # re-raise — kill must reach the top
except Exception:
    log.error("agent failed", exc_info=True)
```

`@guarded` follows this rule — it catches `NullRunError`
(`Exception` subclasses) and lets `BaseException` (kill, pause,
KeyboardInterrupt) propagate.

## See also

- [Reference → Errors](../reference/errors.md) — full catalog
- [Troubleshooting](../troubleshooting.md) — common questions and
  their fixes
- [Use with FastAPI](../how-to/fastapi.md) — exception handling
  inside ASGI handlers
- [Tracing](tracing.md) — how errors map to spans
