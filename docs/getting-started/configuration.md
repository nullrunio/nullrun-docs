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
| `NULLRUN_GATE_CACHE_DISABLE` | `0` | When `1`, disables the in-process 5s gate cache used by chain-mode `@protect` calls (forces a fresh `/gate` round-trip on every call). Use in smoke tests or whenever you need live gate decisions on every invocation — see [Concepts → Budgets](concepts/budgets.md#v3-protocol-negotiation). |
| `NULLRUN_V3_TRACK_DISABLE` | `0` | When `1`, falls back to legacy `/track/batch` instead of the v3 single-event `/api/v1/track` path. Only set this against a v1/v2-only backend; every shipped 1.0.0 backend supports v3. |

The HTTP request timeout and retry count are **not** configurable from
the SDK — they are hardcoded to `30s` and `3` retries. To change
them, build a `NullRunRuntime` directly.

The control-plane transport (WS push vs. HTTP polling fallback) is
configured on the `NullRunRuntime` constructor, not via env var.
The default is WS push with HTTP polling fallback when the WS
connection drops more than `_MAX_RECONNECT_ATTEMPTS` (10) times in
a row. To force HTTP-only from start, construct the runtime with
`polling=True`.

The HMAC signature window (`NULLRUN_HMAC_MAX_AGE_SECS`) and
`NULLRUN_HMAC_REQUIRED` flag are **server-side** settings, not SDK
env vars. The SDK signs every request automatically when
`NULLRUN_SECRET_KEY` is set. The **gateway default** for
`NULLRUN_HMAC_REQUIRED` is `false` (env-var-only policy so operators
must set it explicitly); production deployments must set it to
`true`. When set, the server rejects unsigned SDK traffic with 401
and the SDK-auth middleware emits a per-request WARN so the gap is
visible in logs.

`NULLRUN_HMAC_MAX_AGE_SECS` defaults to `300` (5 minutes).

## Test / dev opt-outs

| Variable | When to use | Risk |
| --- | --- | --- |
| `NULLRUN_SKIP_BUDGET_CHECK=1` | Skip the pre-flight `/gate` check | Agent may overspend before `/track` reconciles. **Full billing bypass**, not just check bypass — emits `RuntimeWarning` at import. |
| `NULLRUN_SENSITIVE_FAIL_OPEN=1` | Sensitive tools allow when gateway is down (test only) | Sensitive tool runs without policy check. The opposite of the production fail-CLOSED default. Emits `RuntimeWarning` at import. |
| `NULLRUN_POLICY_FAIL_OPEN=1` | Restore the pre-fix permissive policy-fetch fallback (test only) | Backend outage silently widens limits — every cost-bearing call is allowed until the next successful fetch. Emits `RuntimeWarning` at import. |

All three **emit a `RuntimeWarning`** at import time so they can't
slip into production unnoticed.

Disabling the WebSocket control plane is an internal test knob — it
is **not** a public env var.

## See also

- [HTTP API](../reference/http-api.md)
- [Control plane](../concepts/control-plane.md)
- [Circuit breaker](../concepts/circuit-breaker.md)
