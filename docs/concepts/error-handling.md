# Error handling

Errors in NullRun come in three layers, designed for three audiences:
your code, your monitoring, and your end users. The SDK does most of
the work — you pick how much of each layer to use.

## Where errors appear in the dashboard

Every error the SDK raises lands in **Governance → Decision History**
and **Governance → Audit log**:

- **Decision History** — the most recent N decisions per workflow,
  with the reason (budget exceeded, rate limit, sensitive tool,
  loop). Useful for "what just happened?"
- **Audit log** — every decision ever, filterable by workflow, time
  range, decision type, tool name. Useful for compliance review
  and incident forensics.

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
| `error_code` | Stable identifier | `"NR-B004"` (budget), `"NR-R001"` (rate limit), `"NR-T001"` (tool blocked) |
| `user_action` | What to do next | `"Wait 30s, then retry"` |
| `retryable` | True if retry-after-backoff makes sense | `True` for rate limit, `False` for budget |
| `docs_url` | URL to the per-code docs page | `"https://docs.nullrun.io/reference/errors#NR-R001"` |

You catch a specific exception type and inspect the fields:

```python
from nullrun import RateLimitError

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

The full exception catalog is in [Reference → Errors](../reference/errors.md).
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
