# Configuration

NullRun reads configuration from environment variables. `init()` only
needs the API key — everything else has sensible defaults.

## Required

| Variable | Description |
| --- | --- |
| `NULLRUN_API_KEY` | API key from the NullRun dashboard (`nr_live_...`) |

## Recommended for production

| Variable | Default | Description |
| --- | --- | --- |
| `NULLRUN_SECRET_KEY` | unset (warns) | HMAC-SHA256 signing secret. Required when the gateway runs with `NULLRUN_HMAC_REQUIRED=true` (the production default). |
| `NULLRUN_API_URL` | `https://api.nullrun.io` | Gateway REST base URL |
| `NULLRUN_WS_URL` | `wss://api.nullrun.io/ws/control` | WebSocket control plane URL. Set to empty to disable WS and fall back to polling. |

## Behaviour

| Variable | Default | Description |
| --- | --- | --- |
| `NULLRUN_BATCH_SIZE` | `100` | Event batch size for `/track/batch` |
| `NULLRUN_FLUSH_INTERVAL_MS` | `5000` | Event flush interval (ms) |
| `NULLRUN_FALLBACK_MODE` | `permissive` | One of `strict` / `permissive` / `cached` (see [Circuit breaker](../concepts/circuit-breaker.md)). Lowercase is required — the SDK reads the value as a string and normalises to lowercase. |

The HTTP request timeout and retry count are **not** configurable from
the SDK — they are hardcoded to `30s` and `3` retries in
`nullrun.runtime.NullRunRuntime` (see the docstring there). To change
them, build a `NullRunRuntime` directly.

The HMAC signature window (`NULLRUN_HMAC_MAX_AGE_SECS`) and
`NULLRUN_HMAC_REQUIRED` flag are **server-side** settings
(`backend/src/config.rs`), not SDK env vars. The SDK signs every
request automatically when `NULLRUN_SECRET_KEY` is set; the server
rejects unsigned SDK traffic with 401 when `NULLRUN_HMAC_REQUIRED=true`
(the production default).

## Test / dev opt-outs

| Variable | When to use | Risk |
| --- | --- | --- |
| `NULLRUN_SKIP_BUDGET_CHECK=1` | Skip the pre-flight `/check` (test only) | Agent may overspend before `/track` sees it |
| `NULLRUN_SENSITIVE_FAIL_OPEN=1` | Sensitive tools allow when gateway is down (test only) | Sensitive tool runs without policy check |

Both **emit a `RuntimeWarning`** at import time so they can't slip
into production unnoticed.

Disabling the WebSocket control plane is an internal test knob — it
is **not** a public env var. To turn it off, construct the runtime
directly with `polling=False`:

```python
from nullrun.runtime import NullRunRuntime
rt = NullRunRuntime(api_key=..., polling=False)   # poll-only mode
```

See `nullrun.__init__` for the rationale ("an internal/test-only
knob").

## gRPC transport — frozen

The gRPC transport exists as an internal scaffold (see
`backend/src/proxy/grpc/`) but is **not available to SDK or dashboard
clients**:

- `grpc-server` reflection is behind a feature flag.
- Production builds fail-fast if the gRPC listener is enabled.
- No SDK generates a gRPC client; the public surface is HTTP only.

If you need lower-latency SDK transport, monitor the changelog — the
frozen status is a deliberate "do not adopt" signal until HMAC parity,
proto extensions, and cost-pipeline parity are proven.

## See also

- [HTTP API](../reference/http-api.md)
- [Control plane](../concepts/control-plane.md)
- [Circuit breaker](../concepts/circuit-breaker.md)
