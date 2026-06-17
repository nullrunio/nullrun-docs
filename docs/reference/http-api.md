# HTTP API

This page summarises the endpoints a typical SDK or dashboard user
interacts with. The OpenAPI spec is the source of truth and is
validated by CI on every PR.

Base URL:

- Production: `https://api.nullrun.io/api/v1`
- Local: `http://localhost:8080/api/v1`

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

### `Authorization: Bearer <session_token>` (dashboard / admin)

Dashboard and admin endpoints (`/orgs/...`, `/admin/...`) use session
tokens obtained from `POST /api/v1/auth/login` or the OAuth flow
(`/auth/oauth/register`). Pass as `Authorization: Bearer <token>`.

## SDK endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/track` | Single event (cost, tokens, latency) |
| `POST` | `/api/v1/track/batch` | Batched events (≤ 100 per batch) |
| `POST` | `/api/v1/gate` | Unified enforcement (replaces `/check` + `/execute` for most SDK flows) |
| `POST` | `/api/v1/execute` | Full policy evaluation + budget reservation |
| `POST` | `/api/v1/check` | Binary budget pre-flight (no reservation) |

## Auth

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/auth/register` | Create account, returns API key + secret |
| `POST` | `/api/v1/auth/login` | Dashboard session token |
| `POST` | `/api/v1/auth/verify` | Verify API key + HMAC |
| `POST` | `/api/v1/auth/oauth/register` | OAuth signup |

## Workflows

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/orgs/{org_id}/workflows` | Create workflow |
| `GET` | `/api/v1/orgs/{org_id}/workflows` | List workflows |
| `GET` | `/api/v1/orgs/{org_id}/workflows/{workflow_id}` | Get workflow |
| `PATCH` | `/api/v1/orgs/{org_id}/workflows/{workflow_id}` | Update (budget, name, …) |
| `POST` | `/api/v1/orgs/{org_id}/workflows/{workflow_id}/pause` | Pause |
| `POST` | `/api/v1/orgs/{org_id}/workflows/{workflow_id}/resume` | Resume |
| `POST` | `/api/v1/orgs/{org_id}/workflows/{workflow_id}/kill` | Kill (broadcasts `StateChange` over WS) |

## Policies

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/orgs/{org_id}/policies` | Create |
| `GET` | `/api/v1/orgs/{org_id}/policies` | List |
| `GET/PATCH/DELETE` | `/api/v1/orgs/{org_id}/policies/{policy_id}` | One policy |

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

## Health, metrics, admin

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/health` | Liveness |
| `GET` | `/api/v1/metrics/prometheus` | Prometheus scrape |
| `GET/PATCH` | `/api/v1/admin/pricing` | Admin pricing |
| `GET/PATCH` | `/api/v1/admin/pricing/{model_id}` | Per-model |
| `POST` | `/api/v1/admin/pricing/missing` | Backfill |

## WebSocket control plane

| Path | Purpose |
| --- | --- |
| `WS /ws/control/{org_id}` | Real-time kill/pause/policy-invalidated/key-rotated events (HMAC-signed on connect) |

See [Control plane](../concepts/control-plane.md) for the message
types (`InitialState`, `StateChange`, `PolicyInvalidated`,
`KeyRotated`, `Pong`, `Subscribed`, `ResyncRequired`, `Error`, `Ack`).

## See also

- [Errors](errors.md)
- [Control plane](../concepts/control-plane.md)
