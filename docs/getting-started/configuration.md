# Configuration

NullRun reads configuration from environment variables. `nullrun.init()`
only needs the API key — everything else has sensible defaults.

Variables are split into two groups: **SDK env vars** are read by the
Python SDK process; **server-side env vars** are read by the gateway
process and only take effect there. Mixing them up (e.g. setting
`NULLRUN_HMAC_REQUIRED=1` on the SDK side) does nothing — the SDK has
no way to enforce server policy.

## SDK env vars

Read by `nullrun.init` and the SDK transport. None of these affect the
gateway.

| Variable | Default | Description |
| --- | --- | --- |
| `NULLRUN_API_KEY` | unset (required) | API key from the NullRun dashboard (`nr_live_...`). Missing at `init()` raises `NullRunAuthenticationError` (NR-C001). |
| `NULLRUN_API_URL` | `https://api.nullrun.io` | Gateway REST base URL. The WebSocket control plane URL is derived — `wss://<api-host>/ws/control` — and is **not** a separate env var. |
| `NULLRUN_SECRET_KEY` | unset | HMAC-SHA256 signing secret. The SDK signs every request automatically when this is set. Whether the gateway *verifies* the signature is controlled by the server-side `NULLRUN_HMAC_REQUIRED` (default `false`). |
| `NULLRUN_ENV` | unset | Environment tag (`production` / `staging` / ...). Used by prod-guard logic — e.g. `NULLRUN_SKIP_BUDGET_CHECK` and `NULLRUN_SENSITIVE_FAIL_OPEN` opt-outs require a second explicit ack in production. |
| `NULLRUN_SKIP_BUDGET_CHECK` | unset | Dev/test opt-out — full bypass of `/gate` budget pre-flight. Production requires a second ack (`NULLRUN_ALLOW_SKIP_BUDGET_CHECK=1`); absent that, the SDK raises at `init()`. |
| `NULLRUN_SENSITIVE_FAIL_OPEN` | unset | `=1` makes sensitive-tool transport errors fail-OPEN. Dev/test only. |
| `NULLRUN_APPROVAL_TIMEOUT_SECONDS` | `300` | SDK-side wait for the `approval_resolved` WS push before fail-CLOSED kill. The server-authoritative wait duration lives on `approval_rule.expires_in_seconds`, clamped server-side to `[1, 3600]`. |
| `NULLRUN_REQUEST_TIMEOUT` | `30` | HTTP request timeout in seconds. |
| `NULLRUN_TRANSPORT` | `ws` | Control-plane transport mode (`ws` or `http`). |
| `NULLRUN_GATE_CACHE_DISABLE` | unset | `=1` disables the SDK's local gate cache (force `/check` on every call). |
| `NULLRUN_V3_TRACK_DISABLE` | unset | `=1` forces the v1 `/track` wire shape. |
| `NULLRUN_TLS_CLIENT_CERT` / `NULLRUN_TLS_CLIENT_KEY` / `NULLRUN_TLS_CA_CERT` | unset | Optional mTLS material for the SDK-to-gateway connection. |
| `NULLRUN_WAL_PATH` / `NULLRUN_WAL_MAX_BYTES` | unset | Write-ahead-log path and size cap for offline event replay. |
| `NULLRUN_MAX_RESPONSE_BYTES` | library default | Cap on captured LLM response body size for span metadata. |

`init(debug=True)` flips the SDK logger to `DEBUG`; there is no env-var
equivalent.

`NULLRUN_USE_GRPC` is **not** an SDK flag — the SDK raises at `init()`
if it sees it (the gRPC transport was prototyped and removed; the env
var is reserved for a future release).

## Server-side env vars

Read by the gateway (`breaker-core`). The SDK does **not** see these —
it only learns their effect via the responses it gets back. Each
fail-CLOSED guard refuses to start the gateway in production
(`BREAKER_ENV=production`) unless the listed escape hatch is also set.

| Env var | Default | Production behaviour |
| --- | --- | --- |
| `NULLRUN_DEV_MODE` | unset | Refuse-to-start in production; dev mode requires explicit opt-in. |
| `NULLRUN_HMAC_REQUIRED` | **`false`** | Default is `false` (env-var-only policy so operators must set it explicitly). When `true`, the gateway verifies the HMAC-SHA256 signature on every SDK request; unsigned traffic is rejected with 401 and the SDK-auth middleware emits a per-request WARN. Production deployments must set `=true`. Escape hatch for emergencies: `NULLRUN_SKIP_HMAC_PROD_CHECK=1`. Without `NULLRUN_HMAC_REQUIRED=true`, the gateway refuses to start in production. |
| `NULLRUN_HMAC_MAX_AGE_SECS` | `300` | Max age (seconds) for a signature's timestamp. |
| `NULLRUN_USE_GRPC` | unset | Without `NULLRUN_GRPC_UNSAFE_ALLOW=1`, the gRPC listener refuses to start. gRPC has no auth, no TLS, and exposes proto via reflection. |
| `NULLRUN_SKIP_BUDGET_CHECK` | unset | Refuse-to-start unconditionally. **No escape hatch** — the bypass itself is the security hole. |
| `NULLRUN_GEOBLOCK_DISABLED` | unset | Refuse-to-start without `NULLRUN_SAFETY_BYPASS_ALLOW=1`. Geo-IP layer. |
| `NULLRUN_SANCTIONS_SCREENING_DISABLED` | unset | Refuse-to-start without `NULLRUN_SAFETY_BYPASS_ALLOW=1`. OFAC SDN name-list screening. |
| `NULLRUN_COST_ROUNDING` | `Nearest` | Per-event cost-rounding mode. Accepts `nearest` (default, balanced), `down` / `truncate` / `floor` (budget-tight), `up` / `ceil` / `ceiling` / `legacy` (legacy over-budget-safe). `up` is **rejected at startup in production** — it inflates every sub-cent event by 1¢ and silently overcharges customers by cents-on-the-dollar. Unrecognised values silently fall back to `Nearest`. |

`NULLRUN_SAFETY_BYPASS_ALLOW=1` is a **shared** escape hatch — it
opens both the geo-IP bypass and the sanctions bypass simultaneously
because the two are two sides of the same compliance control.

### Server-side runtime flags

Runtime switches, not safety controls. Defaults are tuned for
production. Most fail-CLOSED in production if flipped to their legacy
value — override only with a concrete reason.

| Env var | Default | Description |
| --- | --- | --- |
| `NULLRUN_RESERVE_V3_ENABLED` | `1` | Current reserve path (server-minted execution_id). `=0` forces the legacy client-supplied execution_id path and is rejected at startup in production. |
| `NULLRUN_CONSUME_V3_ENABLED` | `1` | Current consume path — server-minted execution_id + atomic digest compare. `=0` rejected at startup in production. |
| `NULLRUN_SOFT_LIMIT_ENABLED` | `1` | Soft budget mode honored fleet-wide. `=0` for incident-response only — the gate logs a warning per downgrade. |
| `NULLRUN_USE_OUTBOX_FOR_TRACK` | `1` | `/track` writes go through the Postgres outbox, then drained async. `=0` disables both enqueue and drain (single flag, two legs). |
| `NULLRUN_RATE_LIMIT_ALGORITHM` | `token_bucket` | Token bucket is the production default. `=fixed` rolls back to the legacy fixed-window path. |
| `NULLRUN_USE_PLAN_FOR_COST_EVENTS` | `0` | Opt-in per-plan retention for `cost_events` instead of the cross-tenant partition-drop path. |

## Behaviour

The HTTP request timeout and retry count are configurable via
`NULLRUN_REQUEST_TIMEOUT` (default `30`s). To change the retry count,
build a `NullRunRuntime` directly.

The control-plane transport (WS push vs. HTTP polling fallback) is
configured by `NULLRUN_TRANSPORT` (default `ws`) or directly on the
`NullRunRuntime` constructor. The default is WS push with HTTP polling
fallback when the WS connection drops more than 10 times in a row. To
force HTTP-only from start, construct the runtime with
`polling=True`.

HMAC signature window (`NULLRUN_HMAC_MAX_AGE_SECS`, default `300`s) and
`NULLRUN_HMAC_REQUIRED` are **server-side** settings, not SDK env vars.
The SDK signs every request automatically when `NULLRUN_SECRET_KEY`
is set; the gateway only verifies the signature when
`NULLRUN_HMAC_REQUIRED=true`.

## See also

- [HTTP API](../reference/http-api.md)
- [Control plane](../concepts/control-plane.md)
- [Circuit breaker](../concepts/circuit-breaker.md)
