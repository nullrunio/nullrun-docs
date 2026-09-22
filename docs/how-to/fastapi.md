---
title: Fastapi
description: Bind a FastAPI request to a NullRun workflow, propagate trace context, and map gate errors to the right HTTP status code.
---

# Use with FastAPI

Install with the FastAPI extra (pulls in `fastapi`, `starlette`, and
the `httpx`-based transport the SDK needs at runtime):

```bash title="shell"
pip install "nullrun[fastapi]" fastapi uvicorn
```

`nullrun.integrations.fastapi.install(app)` is a one-line setup that
turns every NullRun exception in your agent API into a clean JSON
response. Kill signals, budget caps, transport outages, and tool
blocks all render as proper HTTP responses with end-user-safe text
in the body.

```python title="fastapi_app.py"
from fastapi import FastAPI
import nullrun
from nullrun.integrations.fastapi import install

nullrun.init(api_key="nr_live_...")
app = FastAPI()
install(app)

@app.post("/chat")
@nullrun.protect
def chat(message: str) -> dict:
    return {"reply": agent.run(message)}
```

## What `install()` registers

`install(app)` wires the SDK exceptions to FastAPI's handler
chain: every `NullRunError` subclass — including `WorkflowKilledInterrupt`
/ `NullRunWorkflowKilledError` — is routed to the appropriate
`app.add_exception_handler` based on its category.

| Exception | Mechanism | HTTP | Body |
| --- | --- | --- | --- |
| `NullRunError` (budget, tool block, rate limit, soft block, etc.) | `app.add_exception_handler` | per `error_code` | `user_message`, `category: "decision"`, `retryable` |
| Infrastructure errors (transport, 5xx, auth, config) | `app.add_exception_handler` | `503` | `user_message`, `category: "infrastructure"`, `retryable` |
| `WorkflowKilledInterrupt` (alias `NullRunWorkflowKilledError`) | `NullRunMiddleware` (ASGI) | `503` | `user_message`, `category: "killed"` |

`Retry-After` is set on the response whenever the exception carries a
`retry_after` (gateway 429) or `resume_after` (workflow pause)
attribute.

## HTTP status mapping

The status codes below come from `_DECISION_STATUS` and
`_DEFAULT_DECISION_STATUS = 429` / `_DEFAULT_INFRASTRUCTURE_STATUS = 503`
in `nullrun.integrations.fastapi`. SDK exception classes (`exceptions.py`)
carry an `error_code` attribute; the integration maps it to HTTP at
install time.

| `error_code` | Category | HTTP | Notes |
| --- | --- | --- | --- |
| `NR-B004` | decision | `429` | `retryable: false`. Covers `BUDGET_HARD_BLOCKED`, `BUDGET_SOFT_BLOCKED`, `BUDGET_OVERDRAFT_EXCEEDED`, `BUDGET_ANTI_DOS_RESERVED_CAP`, `BUDGET_PERIOD_NOT_STARTED`. Per `_DECISION_STATUS["NR-B004"]`. |
| `NR-R001` | infrastructure | `503` | `Retry-After` from `.retry_after`. Class is `RateLimitError(NullRunTransportError)` so it lands on the infrastructure handler despite the `_DECISION_STATUS["NR-R001"]=429` entry being unreachable in practice. |
| `NR-R002` | infrastructure | `503` | `retryable: true` — Redis unavailable for aggregate rate limit (fail-CLOSED). Class is `NullRunRateLimitRedisError(NullRunInfrastructureError)`. |
| `NR-T001` | decision | `403` | The action itself is forbidden |
| `NR-W004` | decision | `429` | Workflow soft-deleted or killed (`NullRunWorkflowInactiveError`). No `_DECISION_STATUS` entry → falls through to `_DEFAULT_DECISION_STATUS=429`. |
| `NR-W003` | decision | `503` | Workflow paused (`WorkflowPausedException`) — override default to signal server-driven resume |
| `NR-CH001` | decision | `429` | Chain context invalid (chain_id / parent_execution_id). No `_DECISION_STATUS` entry → default 429. |
| `NR-X001` | decision | `403` | Generic block (catch-all decision) |

`WorkflowKilledInterrupt` always maps to `503` (caught by the ASGI
middleware, not the exception-handler chain — Starlette refuses
`BaseException` subclasses in `add_exception_handler`). See
[Reference → Errors](../reference/errors.md) for the full catalog.

## Locale resolution

By default the integration reads `Accept-Language` from the request.
Pass a custom resolver when the locale comes from somewhere else
(session cookie, JWT claim, upstream header):

```python
app = FastAPI()

# Locale from a session cookie, falling back to "en".
install(
    app,
    locale_resolver=lambda req: req.cookies.get("locale", "en"),
)
```

A buggy resolver degrades silently to `"en"`.

## Custom exception mapping

If you want to override `install()`'s defaults for a single endpoint
(rare), wrap the agent call and map the exception yourself:

```python title="custom_mapping.py"
from fastapi import HTTPException
from nullrun import (
    NullRunDecision,
    NullRunInfrastructureError,
    WorkflowKilledInterrupt,
    format_user_message,
)

@app.post("/chat")
@nullrun.protect
def chat(message: str) -> dict:
    try:
        return {"reply": agent.run(message)}
    except NullRunDecision as exc:
        # Expected policy outcome — pass it to the client as-is
        raise HTTPException(
            status_code=exc.status_code or 403,
            detail={
                "message": format_user_message(exc),
                "code": exc.error_code,
                "retryable": exc.retryable,
            },
        )
    except NullRunInfrastructureError as exc:
        # System failure — log to Sentry, return generic 503
        sentry_sdk.capture_exception(exc)
        raise HTTPException(
            status_code=exc.status_code or 503,
            detail={"message": format_user_message(exc), "code": exc.error_code},
        )
```

`WorkflowKilledInterrupt` is caught by the `NullRunError` handler
chain and surfaced as a `503` with `category: "killed"`. Catch it
explicitly in your endpoint if you need to checkpoint before the
response is returned.

## Response body shape

```json
{
  "error_code": "NR-B004",
  "user_message": "You've reached the usage limit for this conversation. Please try again later.",
  "category": "decision",
  "retryable": false
}
```

| Field | Type | Notes |
| --- | --- | --- |
| `error_code` | `string` | Stable machine-readable identifier |
| `user_message` | `string` | End-user-safe text. Safe to render verbatim in a UI |
| `category` | `"decision"` \| `"infrastructure"` \| `"killed"` | Coarse classification for client-side branching |
| `retryable` | `bool` | Mirrors the SDK exception's `.retryable` |

## Per-deployment wording overrides

To brand the wording for a single deployment, call
`nullrun.set_user_message(...)` once at the top of your entry point
(or register via `atexit`):

```python
nullrun.set_user_message(
    "NR-B004",
    "You've used all your support credits. Upgrade to keep chatting.",
)
```

## Limitations

- `app.add_exception_handler` is last-wins — if you already register
  a `NullRunError` handler, `install()` overwrites it. Re-order
  your `install()` call to last if you need custom precedence.
- Kill middleware is process-global state. The locale resolver is
  stored at module level; if you serve multiple FastAPI apps from
  one process with different locale policies, the last `install()`
  call wins. Per-app middleware
  (`app.add_middleware(NullRunMiddleware, locale_resolver=...)`) is
  the supported escape hatch.

## See also

- [Quickstart](../getting-started/quickstart.md)
- [Errors](../reference/errors.md)
