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

## Server-side fail-CLOSED guards

These flags live on the gateway, not on the SDK. The SDK passes through
whatever the server enforces. Each one refuses-to-start the gateway in
production (`BREAKER_ENV=production`) unless the listed escape hatch is
also set.

| Env var | Default | Production behaviour |
| --- | --- | --- |
| `NULLRUN_DEV_MODE` | unset | Refuse-to-start if `NODE_ENV=production`; dev mode requires an explicit two-signal opt-in. |
| `NULLRUN_HMAC_REQUIRED` | unset | Production requires `=true`. Without it, the gateway refuses to start. Escape hatch: `NULLRUN_SKIP_HMAC_PROD_CHECK=1` for genuine emergencies. |
| `NULLRUN_USE_GRPC` | unset | Without `NULLRUN_GRPC_UNSAFE_ALLOW=1`, the gRPC listener refuses to start. gRPC has no auth, no TLS, and exposes proto via reflection. |
| `NULLRUN_SKIP_BUDGET_CHECK` | unset | Refuse-to-start unconditionally. **No escape hatch** — the bypass itself is the security hole. |
| `NULLRUN_GEOBLOCK_DISABLED` | unset | Refuse-to-start without `NULLRUN_SAFETY_BYPASS_ALLOW=1`. Geo-IP layer (Fortress). |
| `NULLRUN_SANCTIONS_SCREENING_DISABLED` | unset | Refuse-to-start without `NULLRUN_SAFETY_BYPASS_ALLOW=1`. OFAC SDN name-list screening. |

`NULLRUN_SAFETY_BYPASS_ALLOW=1` is a **shared** escape hatch — it
opens both the geo-IP bypass and the sanctions bypass simultaneously
because the two are two sides of the same compliance control. Splitting
into separate flags is a documented future-work item.

## Feature flags

These are runtime switches, not safety controls. Defaults are tuned for
production. Override only when you have a concrete reason.

| Env var | Default | Description |
| --- | --- | --- |
| `NULLRUN_RESERVE_V3_ENABLED` | `1` | v3 reserve path (`reserve_v3.lua`). Set to `0` to force the legacy client-supplied execution_id path. |
| `NULLRUN_CONSUME_V3_ENABLED` | `1` | v3 consume path (`consume_v3.lua`) — server-minted execution_id + atomic digest compare. Set to `0` only for legacy SDK compatibility. |
| `NULLRUN_SOFT_LIMIT_ENABLED` | `1` | Soft budget mode is honored fleet-wide. Set to `0` for incident-response only — the gate logs `tracing::warn!` per downgrade. |
| `NULLRUN_USE_OUTBOX_FOR_TRACK` | `1` | `/track` writes go through the Postgres outbox, then drained async. Set to `0` to disable both enqueue and drain (single flag, two legs). |
| `NULLRUN_RATE_LIMIT_ALGORITHM` | `token_bucket` | Token bucket is the production default. Set to `fixed` for rollback to the legacy fixed-window path. |
| `NULLRUN_USE_PLAN_FOR_COST_EVENTS` | `0` | Opt-in per-plan retention for `cost_events` instead of the cross-tenant partition-drop path. |
| `NULLRUN_APPROVAL_TIMEOUT_SECONDS` | `300` | SDK-side wait for `approval_resolved` WS push before fail-CLOSED kill. The server-authoritative wait duration lives on `approval_rule.expires_in_seconds`, clamped server-side to `[1, 3600]` seconds. |

## Behaviour

The HTTP request timeout and retry count are not configurable from the
SDK — they are hardcoded to `30s` and `3` retries. To change them,
build a `NullRunRuntime` directly.

The control-plane transport (WS push vs. HTTP polling fallback) is
configured on the `NullRunRuntime` constructor, not via env var. The
default is WS push with HTTP polling fallback when the WS connection
drops more than `_MAX_RECONNECT_ATTEMPTS` (10) times in a row. To
force HTTP-only from start, construct the runtime with `polling=True`.

The HMAC signature window and `NULLRUN_HMAC_REQUIRED` flag are
**server-side** settings, not SDK env vars. The SDK signs every request
automatically when `NULLRUN_SECRET_KEY` is set. The **gateway default**
for `NULLRUN_HMAC_REQUIRED` is `false` (env-var-only policy so operators
must set it explicitly); production deployments must set it to `true`.
When set, the server rejects unsigned SDK traffic with 401 and the
SDK-auth middleware emits a per-request WARN so the gap is visible in
logs.

## See also

- [HTTP API](../reference/http-api.md)
- [Control plane](../concepts/control-plane.md)
- [Circuit breaker](../concepts/circuit-breaker.md)
