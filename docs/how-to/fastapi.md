# Use with FastAPI

Install with the FastAPI extra (pulls in `fastapi`, `starlette`, and
the `httpx`-based transport the SDK needs at runtime):

```bash title="shell"
pip install "nullrun[fastapi]" fastapi uvicorn
```

`nullrun.integrations.fastapi.install(app)` is a one-line setup that
turns every NullRun exception in your agent API into a clean JSON
response — no per-endpoint `try/except` blocks required. Your route
handlers stay focused on the happy path; kill signals, budget
caps, transport outages, and tool blocks all render as proper HTTP
responses with end-user-safe text in the body.

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

The integration emits canonical machine-readable error codes per
[Reference → Errors](../reference/errors.md). The full catalog lives
in that reference page (e.g. `BUDGET_HARD_BLOCKED`,
`RATE_LIMIT_EXCEEDED`, `TOOL_BLOCKED`, `WORKFLOW_INACTIVE`,
`REDIS_UNAVAILABLE`).

## What `install()` registers

`install(app)` wires three handlers — two via FastAPI's exception
handler chain, one as an ASGI middleware. The split exists because
Starlette refuses `BaseException` subclasses in `add_exception_handler`
(`WorkflowKilledInterrupt` is deliberately a `BaseException` so
careless `except Exception:` handlers in agent code can't swallow
operator kills).

| Exception | Mechanism | HTTP | Body |
| --- | --- | --- | --- |
| `NullRunError` (budget, tool block, rate limit, soft block, etc.) | `app.add_exception_handler` | per `error_code` | `user_message`, `category: "decision"`, `retryable` |
| Infrastructure errors (transport, 5xx, auth, config) | `app.add_exception_handler` | `503` | `user_message`, `category: "infrastructure"`, `retryable` |
| `WorkflowKilledInterrupt` (BaseException) | `NullRunMiddleware` (ASGI) | `503` | `user_message`, `category: "killed"` |

`Retry-After` is set on the response whenever the exception carries a
`retry_after` (gateway 429) or `resume_after` (workflow pause)
attribute.

## HTTP status mapping

The mapping from gate `error_code` to HTTP status:

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

`WorkflowKilledInterrupt` always maps to `503`. The base exception
classes (`NullRunError`, infrastructure variants) carry the
machine-readable `error_code` field — see the catalog in
[Reference → Errors](../reference/errors.md).

## Locale resolution

By default the integration reads `Accept-Language` from the request
and picks the matching `user_message` from the SDK catalog. Pass a
custom resolver when the locale comes from somewhere else (session
cookie, JWT claim, upstream header):

```python title="custom_locale_resolver.py"
from fastapi import FastAPI, Request
import nullrun
from nullrun.integrations.fastapi import install

app = FastAPI()

# Locale from a session cookie, falling back to "en".
install(
    app,
    locale_resolver=lambda req: req.cookies.get("locale", "en"),
)
```

The resolver can return any locale code; in this SDK version only
English is shipped and any non-`"en"` value falls back to the English
message. The parameter is reserved for future locale packs. A buggy
resolver degrades silently to `"en"` — the user still gets a clean
response.

## Response body shape

Every error response has the same shape so the client side can
branch on `category` without parsing strings:

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
| `error_code` | `string` | Stable machine-readable identifier from the catalog |
| `user_message` | `string` | End-user-safe text. Safe to render verbatim in a UI. |
| `category` | `"decision"` \| `"infrastructure"` \| `"killed"` | Coarse classification for client-side branching |
| `retryable` | `bool` | Mirrors the SDK exception's `.retryable` |

The `retryable` field is also surfaced to ops dashboards via the
existing `nullrun.on_error(...)` hook — see
[SDK API → on_error](../reference/sdk-api.md).

## Per-deployment wording overrides

The default `user_message` strings come from the SDK catalog. To
brand the wording for a single deployment (without forking the SDK),
call `nullrun.set_user_message(...)` once at startup:

```python title="branded_message.py"
import nullrun

nullrun.set_user_message(
    "BUDGET_HARD_BLOCKED",
    "You've used all your support credits. Upgrade to keep chatting.",
)
```

Overrides are per-process. See
[Errors → Layer 3 → Branded wording](../concepts/error-handling.md#branded-wording)
for the full override API.

## Limitations

- **`install()` is one-line, but `app.add_exception_handler` is
  last-wins.** If you already register a `NullRunError` handler on
  the same app, `install()` overwrites it. Re-order your `install()`
  call to last if you need custom precedence.
- **Kill middleware is process-global state.** The locale resolver
  is stored at module level. If you serve multiple FastAPI apps
  from one process with different locale policies, the last
  `install()` call wins. Per-app middleware
  (`app.add_middleware(NullRunMiddleware, locale_resolver=...)`) is
  the supported escape hatch.
- **Streaming responses kill recovery is best-effort.** If a kill
  signal fires after the response has started streaming, the
  middleware cannot rewrite the headers — it re-raises the
  `BaseException` and the connection drops. Use timeouts on the
  client side to avoid hanging reads.

## See also

- [Quickstart](../getting-started/quickstart.md)
- [SDK API](../reference/sdk-api.md)
- [Errors → Decision vs. infrastructure](../reference/errors.md)
- [Control plane](../concepts/control-plane.md) — kill mechanism reference
