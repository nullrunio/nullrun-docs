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
| `NULLRUN_API_URL` | `https://api.nullrun.io` | Gateway REST base URL. The WebSocket control plane URL is derived from this — `wss://<api-host>/ws/control` — and is **not** a separate env var. |

## Behaviour

| Variable | Default | Description |
| --- | --- | --- |
| `NULLRUN_BATCH_SIZE` | `50` | Event batch size for `/track/batch` |
| `NULLRUN_FLUSH_INTERVAL_MS` | `5000` | Event flush interval (ms — internally divided by 1000) |
| `NULLRUN_TRANSPORT` | `ws` | Control-plane transport: `ws` (default, WebSocket push) or `http` (1s polling fallback). See `NullRunRuntime._start_remote_polling()` in `src/nullrun/runtime.py`. |
| `NULLRUN_USE_GRPC` | unset (no-op) | Silent no-op — the gRPC transport is frozen. Set to any value; the SDK falls back to HTTP and logs at INFO. |
| `NULLRUN_FALLBACK_MODE` | (deprecated) | Legacy selector — use `on_transport_error` on `Transport.execute()` instead. Emits `DeprecationWarning`, scheduled for removal in 0.5.0. |

The HTTP request timeout and retry count are **not** configurable from
the SDK — they are hardcoded to `30s` and `3` retries in
`nullrun.runtime.NullRunRuntime.__init__` (lines 402-403). To change
them, build a `NullRunRuntime` directly.

The HMAC signature window (`NULLRUN_HMAC_MAX_AGE_SECS`) and
`NULLRUN_HMAC_REQUIRED` flag are **server-side** settings
(`backend/src/config.rs::HmacConfig::from_env`), not SDK env vars. The
SDK signs every request automatically when `NULLRUN_SECRET_KEY` is
set. The **gateway default** for `NULLRUN_HMAC_REQUIRED` is `false`
(env-var-only policy so operators must set it explicitly); production
deployments must set it to `true`. When set, the server rejects
unsigned SDK traffic with 401 and the SDK-auth middleware emits a
per-request WARN so the gap is visible in logs.

`NULLRUN_HMAC_MAX_AGE_SECS` defaults to `300` (5 minutes).

## Test / dev opt-outs

| Variable | When to use | Risk |
| --- | --- | --- |
| `NULLRUN_SKIP_BUDGET_CHECK=1` | Skip the pre-flight `/check` (test only) | Agent may overspend before `/track` sees it |
| `NULLRUN_SENSITIVE_FAIL_OPEN=1` | Sensitive tools allow when gateway is down (test only) | Sensitive tool runs without policy check |
| `NULLRUN_POLICY_FAIL_OPEN=1` | Restore the pre-fix permissive policy-fetch fallback (test only) | Backend outage silently widens limits — every cost-bearing call is allowed until the next successful fetch |

All three **emit a `RuntimeWarning`** at import time so they can't
slip into production unnoticed.

Disabling the WebSocket control plane is an internal test knob — it
is **not** a public env var. To turn it off, construct the runtime
directly with `polling=False`:

```python title="runtime_custom.py"
from nullrun.runtime import NullRunRuntime
rt = NullRunRuntime(api_key=..., polling=False)   # poll-only mode
```

See `nullrun.__init__` for the rationale ("an internal/test-only
knob").

## See also

- [HTTP API](../reference/http-api.md)
- [Control plane](../concepts/control-plane.md)
- [Circuit breaker](../concepts/circuit-breaker.md)
