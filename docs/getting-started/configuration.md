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
| `NULLRUN_TIMEOUT` | `30` | HTTP request timeout (seconds) |
| `NULLRUN_BATCH_SIZE` | `100` | Event batch size for `/track/batch` |
| `NULLRUN_FLUSH_INTERVAL_MS` | `5000` | Event flush interval (ms) |
| `NULLRUN_LOG_LEVEL` | `INFO` | One of `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `NULLRUN_FALLBACK_MODE` | `PERMISSIVE` | One of `STRICT` / `PERMISSIVE` / `CACHED` (see [Circuit breaker](../concepts/circuit-breaker.md)) |
| `NULLRUN_HMAC_REQUIRED` | `true` (prod) / `false` (dev) | When `true`, the gateway rejects unsigned SDK requests with 401. Set to `false` in dev to skip signing. |
| `NULLRUN_HMAC_MAX_AGE_SECS` | `300` | Reject signatures older than N seconds (replay window) |

## Test / dev opt-outs

| Variable | When to use | Risk |
| --- | --- | --- |
| `NULLRUN_SKIP_BUDGET_CHECK=1` | Skip the pre-flight `/check` (test only) | Agent may overspend before `/track` sees it |
| `NULLRUN_SENSITIVE_FAIL_OPEN=1` | Sensitive tools allow when gateway is down (test only) | Sensitive tool runs without policy check |
| `NULLRUN_WS_DISABLED=1` | Disable WebSocket control plane; fall back to polling | Slower kill/pause propagation |

All three **emit a `RuntimeWarning`** at import time so they can't
slip into production unnoticed.

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
