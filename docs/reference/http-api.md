# HTTP API

This page lists the endpoints a user — or their SDK — actually
calls. Internal admin endpoints (pricing backfill, gateway operator
APIs) are not exposed here; see the gateway repo for the full
internal surface.

Base URL:

- Production: `https://api.nullrun.io/api/v1`
- WebSocket control plane: `wss://api.nullrun.io/ws/control`

The OpenAPI spec is generated from the router and is the source of
truth.

## Authentication

Two schemes — they are **not interchangeable**.

### `X-API-Key` + HMAC (SDK → gateway)

All SDK-traffic endpoints (`/track`, `/track/batch`, `/gate`,
`/execute`, `/check`) require:

| Header | Value |
| --- | --- |
| `X-API-Key` | API key (`nr_live_...`) |
| `X-Signature` | hex(HMAC-SHA256(`secret_key`, `timestamp:api_key:body_sha256`)) |
| `X-Signature-Timestamp` | Unix epoch seconds (rejected if older than `NULLRUN_HMAC_MAX_AGE_SECS`, default 300) |
| `X-Workflow-Id` *(optional)* | binds the call to a workflow context |

The SDK computes and signs every request automatically once
`NULLRUN_API_KEY` and `NULLRUN_SECRET_KEY` are set. The gateway
default for `NULLRUN_HMAC_REQUIRED` is `false` for backward
compatibility — operators must set it explicitly to `true` in
production. When `NULLRUN_HMAC_REQUIRED=true`, unsigned SDK requests
are rejected with 401 and the SDK-auth middleware emits a per-request
WARN so the gap is visible in logs.

> SDK requests to `/api/v1/orgs/{org_id}/*` are also checked for
> org-mismatch: the org claimed in the URL must match the org the
> API key was minted for. Mismatch → 403.

### `Authorization: Bearer <session_token>` (dashboard / admin)

Dashboard endpoints (`/orgs/...`, `/admin/...`) use session tokens
obtained from `POST /api/v1/auth/login` or the OAuth flow
(`/auth/oauth/register`). Pass as `Authorization: Bearer <token>`.

## SDK endpoints

These are the endpoints the SDK calls. You will not normally hit
them by hand, but the contracts are stable and the OpenAPI spec
documents every field.

| Method | Path | Called by |
| --- | --- | --- |
| `POST` | `/api/v1/auth/verify` | `init()` — fetches the HMAC `secret_key` for the API key |
| `GET` | `/api/v1/capabilities` | `init()` — protocol negotiation (probes v3 contract support) |
| `POST` | `/api/v1/gate` | Pre-flight + policy evaluation + budget reservation (called from `@protect` entry) |
| `POST` | `/api/v1/track` | v3 single-event commit (`reservation_id` + `idempotency_key`) |
| `POST` | `/api/v1/track/batch` | Legacy batched events (≤ 100 per batch); SDK 0.12.0+ falls back to this only when `NULLRUN_V3_TRACK_DISABLE=1` |
| `GET` | `/api/v1/orgs/{org_id}/policies` | Policy fetch (called from SDK on first `@protect` and on `policy_invalidated` WS push) |
| `GET` | `/api/v1/orgs/{org_id}/workflows/{workflow_id}` | Workflow lookup (called from SDK on first gate per workflow) |
| `GET` | `/api/v1/orgs/{org_id}/status` | Control-plane poll fallback (only used when WS is down) |
| `POST` | `/api/v1/heartbeat` | Time-based cadence heartbeat (v3 contract; replaces the legacy chunk-count v2 path) |

!!! info "Legacy endpoints"
    `/api/v1/check` was removed for new SDK traffic in 0.13.1 and
    now returns `410 Gone` with `replacement: /api/v1/gate`. New
    integrations should target `/gate` directly. `/api/v1/execute`
    is still registered on the gateway for legacy callers but the
    SDK no longer emits traffic against it.

## Auth

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/auth/register` | Create account, returns API key + secret |
| `POST` | `/api/v1/auth/login` | Dashboard session token |
| `POST` | `/api/v1/auth/verify` | Verify API key + return HMAC `secret_key` |
| `POST` | `/api/v1/auth/oauth/register` | OAuth signup (returns API key + secret) |

## Workflows

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/orgs/{org_id}/workflows` | Create workflow |
| `GET` | `/api/v1/orgs/{org_id}/workflows` | List workflows |
| `GET` | `/api/v1/orgs/{org_id}/workflows/{workflow_id}` | Get workflow |
| `PATCH` | `/api/v1/orgs/{org_id}/workflows/{workflow_id}` | Update (budget, name, …) |
| `POST` | `/api/v1/orgs/{org_id}/workflows/{workflow_id}/pause` | Pause (broadcasts `state_change` over WS) |
| `POST` | `/api/v1/orgs/{org_id}/workflows/{workflow_id}/resume` | Resume |
| `POST` | `/api/v1/orgs/{org_id}/workflows/{workflow_id}/kill` | Kill (broadcasts `state_change` over WS) |

## Policies

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/orgs/{org_id}/policies` | Create |
| `GET` | `/api/v1/orgs/{org_id}/policies` | List (a single policy is not addressable by id — read it from the list response) |
| `PATCH` | `/api/v1/orgs/{org_id}/policies/{policy_id}` | Update |
| `DELETE` | `/api/v1/orgs/{org_id}/policies/{policy_id}` | Delete |
| `POST` | `/api/v1/policies/toggle` | Toggle a policy active/inactive (dashboard PATCH 404 fix) |
| `GET` | `/api/v1/orgs/{org_id}/policies/templates` | List policy templates |
| `POST` | `/api/v1/orgs/{org_id}/policies/templates/{template_id}/enable` | Enable a template |
| `DELETE` | `/api/v1/orgs/{org_id}/policies/templates/{template_id}` | Disable a template |

First-match-wins composition — see ADR-007.

## Executions, audit, observability

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/orgs/{org_id}/executions` | List executions |
| `GET` | `/api/v1/orgs/{org_id}/executions/{execution_id}` | One execution |
| `GET` | `/api/v1/orgs/{org_id}/audit-log` | Audit trail |
| `GET` | `/api/v1/orgs/{org_id}/dashboard` | Dashboard payload |
| `GET` | `/api/v1/orgs/{org_id}/quota` | Quota / per-key usage breakdown |
| `GET` | `/api/v1/orgs/{org_id}/status` | Single-call dashboard status (budget + rate + plan limits + time-to-exhaustion) |

## Org management

| Method | Path | Purpose |
| --- | --- | --- |
| `GET/PATCH/DELETE` | `/api/v1/orgs/{org_id}` | Org settings, update, delete |
| `GET` | `/api/v1/orgs/{org_id}/api-keys` | List keys |
| `POST` | `/api/v1/orgs/{org_id}/api-keys` | Mint key |
| `DELETE` | `/api/v1/orgs/{org_id}/api-keys/{key_id}` | Revoke key |
| `POST` | `/api/v1/orgs/{org_id}/api-keys/{key_id}/rotate` | Rotate the HMAC secret in place |
| `GET` | `/api/v1/workflows/{workflow_id}/api-keys` | Per-workflow key listing |
| `GET` | `/api/v1/orgs/{org_id}/members` | Members |
| `PATCH` | `/api/v1/orgs/{org_id}/members/{member_id}` | Update member role |
| `DELETE` | `/api/v1/orgs/{org_id}/members/{member_id}` | Remove member |
| `POST` | `/api/v1/orgs/{org_id}/invites` | Invite |
| `DELETE` | `/api/v1/orgs/{org_id}/invites/{invite_id}` | Revoke invite |
| `POST` | `/api/v1/orgs/{org_id}/invites/{invite_id}/resend` | Resend invite email |
| `GET` | `/api/v1/invites/{token}` | Public invite info |
| `POST` | `/api/v1/invites/{token}/accept` | Public invite accept |
| `POST` | `/api/v1/invites/{token}/decline` | Public invite decline |

## Alerts

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/orgs/{org_id}/alerts` | Active alerts |
| `POST` | `/api/v1/orgs/{org_id}/alerts/{alert_id}/dismiss` | Dismiss |
| `GET/POST` | `/api/v1/orgs/{org_id}/alert-channels` | Channels |
| `GET/PATCH` | `/api/v1/orgs/{org_id}/notification-settings` | Per-user settings |

## Health

Health endpoints are registered on the gateway's top-level router
— they are **not** under `/api/v1`. They return `200 OK` when healthy,
`503` otherwise, with a JSON body listing each dependency's status.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Alias for `/health/live` |
| `GET` | `/healthz` | Alias for `/health/live` (Kubernetes convention) |
| `GET` | `/health/live` | Liveness — process is up and accepting connections |
| `GET` | `/health/ready` | Readiness — Postgres + Redis reachable |
| `GET` | `/health/startup` | Startup — `200` after migrations complete, `503` while booting |

## Capabilities

The capabilities endpoint reports the wire-contract version the
gateway supports. The SDK calls this on `init()` to negotiate
the protocol version (v1/v2 vs. v3) and to surface a startup
warning if the SDK is older than what the gateway requires.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/capabilities` | Report `min_protocol_version` / `max_protocol_version`, `sdk_min_version`, `lua_script_version`, server version + build timestamp, and the `capabilities.*` feature flags (`server_minted_execution_id`, `per_execution_reservations`, `heartbeat_time_based`, `idempotency_keys`, `rate_limit_fail_scope`, etc.) |

The v3 readiness gate (`is_v3_ready()` on the SDK side) requires
all three of `server_minted_execution_id`, `per_execution_reservations`,
and `heartbeat_time_based` to be `true`. If the backend reports
v3-ready but the SDK is older than `0.12.0` (the canonical
`SDK_MIN_VERSION_FOR_V3`), `init()` emits a warning so the
operator sees the gap before the first `/gate` call fails with
`400 PROTOCOL_TOO_OLD`.

## Heartbeat

Long-running workflows post a time-based cadence heartbeat so the
gateway can detect an orphaned workflow whose agent process has
crashed without sending a kill / pause signal. The v3 contract
replaces the legacy chunk-count heartbeat with a wall-clock
interval; the recommended cadence is advertised in
`capabilities.heartbeat_interval_seconds` (default 30s).

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/heartbeat` | Time-based cadence heartbeat (workflow_id + chain_id) |

The SDK posts heartbeats automatically inside the
`NullRunRuntime` background thread once `init()` has run; operators
do not need to call it manually.

## WebSocket control plane

| Path | Purpose |
| --- | --- |
| `WS /ws/control/{org_id}` | Real-time kill/pause/policy-invalidated/key-rotated events (HMAC-signed on connect) |

Server → client message types: `initial_state`, `state_change`,
`policy_invalidated`, `key_rotated`, `resync_required`, `error`,
`pong`, `approval_resolved`, `subscribed`.

Client → server message types: `ack`.

See [Control plane](../concepts/control-plane.md) for the full
protocol and the SDK reaction matrix.

## Not in this page

The following endpoint families are intentionally omitted because
they are gateway-internal, not user-facing. They are documented in
the gateway repo's OpenAPI spec and are not callable from the SDK
or the public dashboard.

- `/api/v1/admin/pricing` and per-model pricing backfill — operator-only
- `/api/v1/metrics/prometheus` — gateway-internal scrape target
- Webhook delivery, outbox processor, internal cron — gateway-internal

## See also

- [Errors](errors.md)
- [Control plane](../concepts/control-plane.md)
