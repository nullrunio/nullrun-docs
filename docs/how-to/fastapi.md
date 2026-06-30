# Use with FastAPI

Install with the FastAPI extra (pulls in `fastapi`, `starlette`, and
the `httpx`-based transport the SDK needs at runtime):

```bash title="shell"
pip install "nullrun[fastapi]" fastapi uvicorn
```

`nullrun.integrations.fastapi.install(app)` is a one-line setup that
turns every NullRun exception in your Customer Support Bot / agent
API into a clean JSON response — no per-endpoint `try/except` blocks
required. Your route handlers stay focused on the happy path; kill
signals, budget caps, transport outages, and tool blocks all render
as proper HTTP responses with end-user-safe text in the body.

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

# POST /chat that triggers a budget cap returns:
#   HTTP 429
#   {"error_code": "NR-B004",
#    "user_message": "You've reached the usage limit for this conversation. Please try again later.",
#    "category": "decision",
#    "retryable": false}
#
# POST /chat that triggers a NullRun backend outage returns:
#   HTTP 503
#   {"error_code": "NR-B001",
#    "user_message": "I'm having trouble connecting. Please try again in a moment.",
#    "category": "infrastructure",
#    "retryable": true}
```

## What `install()` registers

`install(app)` wires three handlers — two via FastAPI's exception
handler chain, one as an ASGI middleware. The split exists because
Starlette refuses `BaseException` subclasses in `add_exception_handler`
(`WorkflowKilledInterrupt` is deliberately a `BaseException` so
careless `except Exception:` handlers in agent code can't swallow
operator kills).

| Exception | Mechanism | HTTP | Body |
| --- | --- | --- | --- |
| `NullRunDecision` (budget, tool block, rate limit, loop, pause) | `app.add_exception_handler` | `429` or `403` or `503` per `error_code` | `user_message`, `category: "decision"`, `retryable` |
| `NullRunInfrastructureError` (transport, 5xx, auth, config) | `app.add_exception_handler` | `503` | `user_message`, `category: "infrastructure"`, `retryable` |
| `WorkflowKilledInterrupt` (BaseException) | `NullRunMiddleware` (ASGI) | `503` | `user_message`, `category: "killed"` |

`Retry-After` is set on the response whenever the exception carries a
`retry_after` (gateway 429) or `resume_after` (workflow pause)
attribute.

## HTTP status mapping

| `error_code` | Category | HTTP | Notes |
| --- | --- | --- | --- |
| `NR-B004` (budget exhausted) | decision | `429` | `retryable: false` — user must upgrade or wait for next cycle |
| `NR-L001` (loop detected) | decision | `429` | User can retry after the loop window |
| `NR-R001` (rate limit) | decision | `429` | `Retry-After` from `.retry_after` |
| `NR-T001` (tool blocked) | decision | `403` | The action itself is forbidden |
| `NR-X001` (generic block) | decision | `403` | Catch-all for unclassified blocks |
| `NR-W003` (workflow paused) | decision | `503` | `Retry-After` from `.resume_after` |
| `NR-W002` (killed) | killed | `503` | Operator-initiated |
| `NR-B001` (network) | infrastructure | `503` | `retryable: true` |
| `NR-B002` (backend 5xx) | infrastructure | `503` | `retryable: true` |
| `NR-B005` (breaker open) | infrastructure | `503` | `retryable: true` |
| `NR-A003` (auth rejected) | infrastructure | `503` | Misconfiguration on the host side |

For the rationale behind the Decision vs. Infrastructure split, see
[Errors → Decision vs. infrastructure](../reference/errors.md#decision-vs-infrastructure).

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
  "error_code": "NR-B004",
  "user_message": "You've reached the usage limit for this conversation. Please try again later.",
  "category": "decision",
  "retryable": false
}
```

| Field | Type | Notes |
| --- | --- | --- |
| `error_code` | `string` | Stable `NR-XXXXX` identifier from the SDK catalog |
| `user_message` | `string` | End-user-safe text. Safe to render verbatim in a UI. |
| `category` | `"decision"` \| `"infrastructure"` \| `"killed"` | Coarse classification for client-side branching |
| `retryable` | `bool` | Mirrors the SDK exception's `.retryable` |

The `retryable` field is also surfaced to ops dashboards via the
existing `nullrun.on_error(...)` hook — see
[SDK API → on_error](../reference/sdk-api.md#top-level).

## Per-deployment wording overrides

The default `user_message` strings come from the SDK catalog. To
brand the wording for a single deployment (without forking the SDK),
call `nullrun.set_user_message(...)` once at startup:

```python title="branded_message.py"
import nullrun

nullrun.set_user_message(
    "NR-B004",
    "You've used all your support credits. Upgrade to keep chatting.",
)
```

Overrides are per-process. See
[SDK API → User-facing messages](../reference/sdk-api.md#user-facing-messages)
for the full override API and the rationale for SDK-owned wording.

## Limitations

- **`install()` is one-line, but `app.add_exception_handler` is
  last-wins.** If you already register a `NullRunError` handler on
  the same app, `install()` overwrites it. Re-order your `install()`
  call to last if you need custom precedence.
- **Kill middleware is process-global state.** The locale resolver is
  stored at module level. If you serve multiple FastAPI apps from one
  process with different locale policies, the last `install()` call
  wins. Per-app middleware (`app.add_middleware(NullRunMiddleware,
  locale_resolver=...)`) is the supported escape hatch.
- **Streaming responses kill recovery is best-effort.** If a kill
  signal fires after the response has started streaming, the
  middleware cannot rewrite the headers — it re-raises the
  `BaseException` and the connection drops. Use timeouts on the
  client side to avoid hanging reads.

## See also

- [Quickstart](../getting-started/quickstart.md)
- [SDK API](../reference/sdk-api.md)
- [Errors → Decision vs. infrastructure](../reference/errors.md#decision-vs-infrastructure)
- [Control plane](../concepts/control-plane.md) — kill mechanism reference
