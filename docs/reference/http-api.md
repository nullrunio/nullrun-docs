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
`NULLRUN_API_KEY` and `NULLRUN_SECRET_KEY` are set. When
`NULLRUN_HMAC_REQUIRED=true` (the production default), unsigned SDK
requests are rejected with 401.

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
| `POST` | `/api/v1/track` | Single cost / token / latency event |
| `POST` | `/api/v1/track/batch` | Batched events (≤ 100 per batch) |
| `POST` | `/api/v1/gate` | Binary budget pre-flight (called from `@protect` entry) |
| `POST` | `/api/v1/execute` | Full policy evaluation + budget reservation (called from `@protect` body) |
| `POST` | `/api/v1/check` | Legacy pre-flight (advisory, no scope check — kept for backward compatibility; new code uses `/gate`) |
| `GET` | `/api/v1/orgs/{org_id}/policies` | Policy fetch (called from SDK on first `@protect` and on `PolicyInvalidated` WS push) |
| `GET` | `/api/v1/orgs/{org_id}/workflows/{workflow_id}` | Workflow lookup (called from SDK on first gate per workflow) |
| `GET` | `/api/v1/orgs/{org_id}/status` | Control-plane poll fallback (only used when WS is down) |

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
| `POST` | `/api/v1/orgs/{org_id}/workflows/{workflow_id}/pause` | Pause (broadcasts `StateChange` over WS) |
| `POST` | `/api/v1/orgs/{org_id}/workflows/{workflow_id}/resume` | Resume |
| `POST` | `/api/v1/orgs/{org_id}/workflows/{workflow_id}/kill` | Kill (broadcasts `StateChange` over WS) |

## Policies

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/orgs/{org_id}/policies` | Create |
| `GET` | `/api/v1/orgs/{org_id}/policies` | List |
| `GET` | `/api/v1/orgs/{org_id}/policies/{policy_id}` | One policy |
| `PATCH` | `/api/v1/orgs/{org_id}/policies/{policy_id}` | Update |
| `DELETE` | `/api/v1/orgs/{org_id}/policies/{policy_id}` | Delete |

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
| `GET/PATCH` | `/api/v1/orgs/{org_id}` | Org settings |
| `GET` | `/api/v1/orgs/{org_id}/api-keys` | List keys |
| `POST` | `/api/v1/orgs/{org_id}/api-keys` | Mint key |
| `DELETE` | `/api/v1/orgs/{org_id}/api-keys/{key_id}` | Revoke key |
| `GET` | `/api/v1/orgs/{org_id}/members` | Members |
| `POST` | `/api/v1/orgs/{org_id}/invites` | Invite |
| `DELETE` | `/api/v1/orgs/{org_id}/members/{member_id}` | Remove |

## Alerts

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/orgs/{org_id}/alerts` | Active alerts |
| `POST` | `/api/v1/orgs/{org_id}/alerts/{alert_id}/dismiss` | Dismiss |
| `GET/POST` | `/api/v1/orgs/{org_id}/alert-channels` | Channels |
| `GET/PATCH` | `/api/v1/orgs/{org_id}/notification-settings` | Per-user settings |

## Health

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/health` | Liveness — `200 OK` if the gateway can reach Postgres + Redis |

## WebSocket control plane

| Path | Purpose |
| --- | --- |
| `WS /ws/control/{org_id}` | Real-time kill/pause/policy-invalidated/key-rotated events (HMAC-signed on connect) |

Server → client message types: `InitialState`, `StateChange`,
`PolicyInvalidated`, `KeyRotated`, `ResyncRequired`, `Error`,
`Pong`.

Client → server message types: `Subscribed`, `Ack`.

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
