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

`install(app)` wires three handlers — two via FastAPI's exception
handler chain, one as an ASGI middleware. The split exists because
Starlette refuses `BaseException` subclasses in
`add_exception_handler` (so careless `except Exception:` handlers in
agent code can't swallow operator kills).

| Exception | Mechanism | HTTP | Body |
| --- | --- | --- | --- |
| `NullRunError` (budget, tool block, rate limit, soft block, etc.) | `app.add_exception_handler` | per `error_code` | `user_message`, `category: "decision"`, `retryable` |
| Infrastructure errors (transport, 5xx, auth, config) | `app.add_exception_handler` | `503` | `user_message`, `category: "infrastructure"`, `retryable` |
| `WorkflowKilledInterrupt` (BaseException) | `NullRunMiddleware` (ASGI) | `503` | `user_message`, `category: "killed"` |

`Retry-After` is set on the response whenever the exception carries a
`retry_after` (gateway 429) or `resume_after` (workflow pause)
attribute.

## HTTP status mapping

| `error_code` | Category | HTTP | Notes |
| --- | --- | --- | --- |
| `BUDGET_HARD_BLOCKED` | decision | `429` | `retryable: false` — user must upgrade or wait for next cycle |
| `BUDGET_OVERDRAFT_EXCEEDED` | decision | `429` | Soft mode exhausted its cap |
| `BUDGET_ANTI_DOS_RESERVED_CAP` | decision | `429` | 30% reservation anti-DoS cap |
| `RATE_LIMIT_EXCEEDED` | decision | `429` | `Retry-After` from `.retry_after` |
| `RATE_LIMIT_REDIS_UNAVAILABLE` | decision | `503` | Aggregate rate limit fails closed |
| `TOOL_BLOCKED` | decision | `403` | The action itself is forbidden |
| `WORKFLOW_INACTIVE` | decision | `403` | Workflow was soft-deleted or killed |
| `CHAIN_MAX_DURATION_EXCEEDED` | decision | `402` | Chain exceeded `max_chain_duration_seconds` |
| `REDIS_UNAVAILABLE` | infrastructure | `503` | `retryable: true` |
| `BUDGET_DATA_UNAVAILABLE` | infrastructure | `503` | ApproximateBudget endpoint: all sources down |

`WorkflowKilledInterrupt` always maps to `503`. See
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

## Response body shape

```json
{
  "error_code": "BUDGET_HARD_BLOCKED",
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
`nullrun.set_user_message(...)` once at startup:

```python
nullrun.set_user_message(
    "BUDGET_HARD_BLOCKED",
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
