---
title: HTTP API
description: The NullRun HTTP surface: the endpoints the SDK calls, the protocol header, request signing, idempotency, and the control-plane endpoints.
maturity: stable
---

# HTTP API

Base URL: `https://api.nullrun.io`.

REST paths start with `/api/v1`. The WebSocket control plane path does not.

Every response body is JSON.

## Protocol header

Every request to a gateway endpoint carries the wire-protocol version:

```http title="HTTP"
X-NULLRUN-PROTOCOL: 4
```

The value is a bare integer. The gateway accepts 2 to 11, and its current
version is 11. The SDK sends 4 on every call, so you never set the header by
hand. A missing or unsupported version answers `400`.

## Authentication

Two schemes. They are not interchangeable.

| Caller | Headers | Credential |
|---|---|---|
| SDK | `X-API-Key` | The API key, for example `nr_live_...` |
| SDK with request signing | `X-API-Key`, `X-Signature`, `X-Signature-Timestamp` | The API key plus the signing secret |
| Dashboard | `Authorization: Bearer <session_token>` | A session token from `POST /api/v1/auth/login` |

The enforcement path reads `X-API-Key`. It does not read
`Authorization: Bearer`, so a call that carries only the bearer token answers
`401` with `API_KEY_MISSING`. The SDK sends both headers.

The signing secret is separate from the API key. It arrives in the
`POST /api/v1/auth/verify` response as `secret_key`.

The signature is the hex-encoded HMAC-SHA256 of this string, keyed with the
signing secret:

```text title="Signature"
<timestamp>:<api_key>:<sha256_hex_of_the_request_body>
```

`X-Signature-Timestamp` carries the Unix epoch seconds used in the signature.
The gateway rejects a stale timestamp with `401`.

The SDK computes the signature for every request on its own. A request body is
signed as the exact bytes that go on the wire. Signing covers the enforcement
calls: `POST /api/v1/gate`, `POST /api/v1/execute`, `POST /api/v1/track`, and
`POST /api/v1/track/batch`.

## SDK endpoints

These are the endpoints the SDK calls. You do not normally call them by hand.

| Method | Path | What it does |
|---|---|---|
| `POST` | `/api/v1/auth/verify` | Verifies the API key. Returns the credential bundle: `organization_id`, `workflow_id`, `secret_key`, `key_version`, plan, features, limits. |
| `GET` | `/api/v1/capabilities` | Reports the supported wire-protocol range, the recommended SDK version, and the feature flags. |
| `POST` | `/api/v1/gate` | Checks the budget for one action and reserves it. Returns the decision and a server-minted `execution_id`. Sending `chain_op: "end"` closes a chain. |
| `POST` | `/api/v1/execute` | Evaluates the policy for one tool call. This is the primary enforcement point. |
| `POST` | `/api/v1/track` | Commits one spend event against a reservation. |
| `POST` | `/api/v1/track/batch` | Commits up to 100 spend events in one request. |
| `POST` | `/api/v1/approvals/{approval_id}/consume` | Closes an approved grant without running the tool. Idempotent. |
| `POST` | `/api/v1/heartbeat` | Reports that a long-running workflow is still alive. The body carries `chain_id`. |
| `POST` | `/api/v1/cancel` | Cancels an in-flight execution. Idempotent. |
| `GET` | `/api/v1/status/{workflow_id}` | Reads the state of one workflow. The SDK polls this when the WebSocket is unavailable. |
| `GET` | `/api/v1/budget/approximate` | Returns the approximate budget view. |
| `GET` | `/api/v1/orgs/{org_id}/audit-log` | Lists audit entries. |
| `GET` | `/api/v1/orgs/{org_id}/audit-log/verify` | Verifies the audit trail. |
| `GET`, `POST` | `/api/v1/orgs/{org_id}/audit-log/export` | Starts an export job and returns a job id. |
| `GET` | `/api/v1/orgs/{org_id}/audit-log/export/{job_id}/status` | Reports the export job status. |
| `WS` | `/ws/control/{organization_id}` | Streams control-plane events: kill, pause, approval decisions, key rotation. |

`POST /api/v1/check` is not served. It answers `410` and names
`POST /api/v1/gate` as the path to use.

### The credential bundle

`POST /api/v1/auth/verify` answers with the fields the SDK needs to run.

| Field | Type | Notes |
|---|---|---|
| `organization_id` | string | The org the key belongs to. Required — a response without it is an error. |
| `organization_name` | string \| null | The org display name. |
| `plan` | string | The plan tier. |
| `features` | object | The plan's feature flags. |
| `limits` | object | The plan's limits. |
| `role` | string \| null | The member role. `null` on the API-key path. |
| `workflow_id` | string \| null | The workflow the key is bound to. `null` on an unbound key. |
| `secret_key` | string \| null | The signing secret. `null` when the key does not sign. |
| `key_version` | number \| null | The active signing-secret version. A change means the secret rotated. |

## The gate call

`POST /api/v1/gate` is the entry point of the enforcement path. It checks the
budget for one action, reserves the money, and answers with a decision.

### Request

| Field | Required | Notes |
|---|---|---|
| `organization_id` | yes | The org the call runs for. |
| `execution_id` | yes | The execution this call belongs to. |
| `trace_id` | yes | The trace this call belongs to. |
| `mode` | yes | `auto`, `inline`, or `strict`. |
| `tool` | no | One tool name. The gate reads `tool` or `tools`, never `tool_name`. |
| `tools` | no | A list of tool names the caller intends to use. |
| `model` | no | The model the call will use, for an LLM check. |
| `estimated_tokens` | no | The input-token estimate, for an LLM check. |
| `max_output_tokens` | no | The caller's own output-token ceiling. |
| `check_type` | no | `llm` or `tool`. |
| `workflow_id` | no | The workflow the call runs for. |
| `chain_id` | no | The chain the call belongs to. |
| `chain_op` | no | `start`, `continue`, or `end`. |
| `approval_id` | no | The approval presented on the post-approval re-check. |
| `business_impact` | no | The value the call moves. Omit it when there is none. |
| `action_digest` | no | Digest of the business impact, re-sent on the re-check. |
| `tool_class` | no | `builtin`, `mcp`, `custom`, or `invalid`. |
| `parent_execution_id` | no | The execution that spawned this one. |

`business_impact` has two kinds. There is no `none` kind — omit the field
instead.

| `kind` | Fields |
|---|---|
| `money` | `direction` (`outflow` or `inflow`), `amount_minor` in cents, `currency`. |
| `tool_call` | `tool_name`, `params`. |

### Decision values

| Decision | Meaning |
|---|---|
| `allow` | The call may run. |
| `block` | The call may not run. |
| `require_approval` | The call may run after an operator approves it. The answer carries an `approval_id`. |
| `soft_pass` | The call runs, and the event is recorded for review. |
| `deny` | The call may not run, and the model may adapt and try something else. |

### Response

| Field | Notes |
|---|---|
| `decision` | One of the five values above. |
| `decision_source` | Which rule produced the decision. |
| `explanation` | The reason, in human text. |
| `execution_id` | The server-minted id for this execution. |
| `approval_id` | The approval to wait on. Present on `require_approval`. |
| `remaining_budget_cents` | The budget left in the period, in cents. |
| `projected_cost_cents` | The reserved cost, in cents. |
| `retry_after_ms` | How long to wait, in milliseconds. |
| `action_digest` | The digest the gateway recorded for the approval. |
| `category` | `denied`, `budget`, `halt`, or `infra`. |
| `budget_enforcement` | `enforced`, `not_configured`, or `unknown`. |
| `user_message` | Text to show the user. |
| `agent_message` | Text to show the model. |

### Money units

Three units appear on the wire. They are not interchangeable.

| Unit | Where it appears |
|---|---|
| Cents, integer | The request wire: `cost_cents`, `reserved_cost_cents`, `budget_cents`, `threshold_cents`, `amount_minor`, `threshold_minor`, `projected_cost_cents`, `remaining_budget_cents`. |
| Millicents, integer | The ledger and the lease responses: `cost_millicents`, `granted_millicents`, `spent_millicents`, `monthly_cost_millicents`. One millicent is 1/1000 of a cent. |
| US dollars, float | The track response snapshot: `total_cost_usd`, `cost_usd`, `rate_per_minute`. |

A field named `projected_cost_millicents` does not exist on the wire. The gate
reports `projected_cost_cents`.

## Idempotency

Two body fields carry the idempotency key.

| Field | Sent on | Value |
|---|---|---|
| `idempotency_key` | `/api/v1/gate`, `/api/v1/track` | A UUID v4 minted by the SDK for the logical action. |
| `operation_id` | `/api/v1/gate`, `/api/v1/execute` | The SDK's name for the same value. |

The gateway binds the reservation to the key, so a repeated call with the same
key settles the same action instead of charging twice. The SDK reuses one
`operation_id` for the whole gate-then-execute-then-track sequence of a single
action.

Two endpoints are idempotent by contract and need no key from you:

- `POST /api/v1/cancel` — a second call on the same execution is a no-op.
- `POST /api/v1/approvals/{approval_id}/consume` — an already-consumed grant
  answers `200`.

## Control-plane endpoints

These endpoints drive the dashboard and the control plane. They are not part
of the SDK's request path.

### Workflows

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/orgs/{org_id}/workflows` | Create a workflow. |
| `GET` | `/api/v1/orgs/{org_id}/workflows` | List workflows. |
| `GET` | `/api/v1/orgs/{org_id}/workflows/{workflow_id}` | Get one workflow. |
| `PATCH` | `/api/v1/orgs/{org_id}/workflows/{workflow_id}` | Update the budget, the name, and other settings. |
| `POST` | `/api/v1/orgs/{org_id}/workflows/{workflow_id}/pause` | Pause the workflow. |
| `POST` | `/api/v1/orgs/{org_id}/workflows/{workflow_id}/resume` | Resume the workflow. |
| `POST` | `/api/v1/orgs/{org_id}/workflows/{workflow_id}/kill` | Kill the workflow. |

The create body carries `name`, `external_id`, and an optional `budget_cents`.
The org-scope key is `external_id`: two workflows may share a `name`, and a
repeated `external_id` matches the existing workflow.

### Policies

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/orgs/{org_id}/policies` | List policies. A single policy is not addressable by id — read it from the list. |
| `POST` | `/api/v1/orgs/{org_id}/policies` | Create a policy. |
| `PATCH` | `/api/v1/orgs/{org_id}/policies/{policy_id}` | Update a policy. |
| `DELETE` | `/api/v1/orgs/{org_id}/policies/{policy_id}` | Delete a policy. |
| `POST` | `/api/v1/orgs/{org_id}/policies/{policy_id}/toggle` | Switch a policy between active and inactive. |
| `GET` | `/api/v1/orgs/{org_id}/policies/templates` | List policy templates. |
| `POST` | `/api/v1/orgs/{org_id}/policies/templates/{template_id}/enable` | Enable a template. |
| `DELETE` | `/api/v1/orgs/{org_id}/policies/templates/{template_id}` | Disable a template. |

The most restrictive applicable policy wins. See
[Concepts → Policies](../concepts/policies.md).

A policy body carries:

| Field | Values |
|---|---|
| `policy_type` | `rate_limit`, `budget_limit`, or `tool_block`. |
| `scope` | `org` or `workflow`. |
| `enforcement_mode` | `Hard` or `Soft`. |

The config keys depend on `policy_type`.

| `policy_type` | Config keys |
|---|---|
| `rate_limit` | `max_calls_per_minute`. An integer. `0` means no limit. |
| `budget_limit` | `budget_cents`. An integer number of cents. |
| `tool_block` | `tool_pattern` — one glob — plus `blocked_tools`, `tools`, and `parameter_conditions`. |

The tool-block key is `tool_pattern`, singular. The plural `tool_patterns` is
rejected with `422`.

### Approvals

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/orgs/{org_id}/approvals` | List approvals. |
| `POST` | `/api/v1/orgs/{org_id}/approvals/{approval_id}/approve` | Approve a pending approval. An already-decided approval answers `409`. |
| `POST` | `/api/v1/orgs/{org_id}/approvals/{approval_id}/deny` | Deny a pending approval. |
| `GET` | `/api/v1/orgs/{org_id}/approvals/history` | List decided approvals. |

### Executions, audit, and usage

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/orgs/{org_id}/executions` | List executions. |
| `GET` | `/api/v1/orgs/{org_id}/executions/{execution_id}` | Get one execution. |
| `GET` | `/api/v1/orgs/{org_id}/audit-log` | List audit entries. |
| `GET` | `/api/v1/orgs/{org_id}/audit-log/verify` | Verify the audit trail. |
| `GET` | `/api/v1/orgs/{org_id}/audit-log/export` | Start an export job. |
| `POST` | `/api/v1/orgs/{org_id}/audit-log/export` | Start an export job. |
| `GET` | `/api/v1/orgs/{org_id}/audit-log/export/{job_id}/status` | Poll the export job. |
| `GET` | `/api/v1/orgs/{org_id}/audit-log/export/{job_id}/download` | Download the exported file. |
| `GET` | `/api/v1/orgs/{org_id}/traces` | List trace spans. |
| `GET` | `/api/v1/orgs/{org_id}/traces/{trace_id}` | Get one trace with its full span tree. |
| `GET` | `/api/v1/orgs/{org_id}/incidents` | List active and recent incidents. |
| `GET` | `/api/v1/orgs/{org_id}/usage` | Usage breakdown. |
| `GET` | `/api/v1/orgs/{org_id}/quota` | Usage breakdown. Same payload as `/usage`. |
| `GET` | `/api/v1/orgs/{org_id}/dashboard` | Dashboard payload. |
| `GET` | `/api/v1/orgs/{org_id}/control-center` | Workflows, recent decisions, and alerts in one call. |

### Budget and status

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/budget/approximate` | Approximate budget view for display. See [Budgets](../concepts/budgets.md#approximate-budget-endpoint). |
| `GET` | `/api/v1/orgs/{org_id}/status` | One call with the spend, the budget, the rate usage, the plan limits, and the plan. |

`GET /api/v1/budget/approximate` answers with the estimate and its
provenance.

| Field | Notes |
|---|---|
| `org_id` | The org the estimate belongs to. |
| `current_spend_cents_estimate` | The estimated spend. |
| `is_approximate` | Always `true`. The endpoint is advisory only. |
| `source` | Where the number came from. |
| `confidence` | How stale the number may be. |
| `last_updated_at` | ISO-8601 UTC of the read. |

The endpoint answers `503` when it cannot produce an estimate. The body
carries `error_code`, `error_message`, and `retry_after_ms`. Render a retry
prompt, not a zero spend.

`GET /api/v1/orgs/{org_id}/status` answers with the org's money and limits.

| Field | Notes |
|---|---|
| `usage_today_cents` | Spend over the last 24 hours. |
| `usage_month_cents` | Spend over the current billing period. |
| `budget_used_cents` | Org budget used in the period. |
| `budget_remaining_cents` | `null` when the plan sets no org budget. |
| `budget_limit_cents` | `null` when the plan budget is unlimited. |
| `budget_pct_used` | `null` when there is no cap. |
| `time_to_limit` | `null` when no exhaustion is projected in the period. |
| `rate` | Rate-limit status for the org. |
| `per_key_rate` | Per-key rate visibility. Absent when not available. |
| `limits` | Plan limits and the current usage against them. |
| `plan`, `plan_name` | The plan tier and its display name. |
| `subscription_status` | `active`, `past_due`, `cancelled`, or `expired`. |
| `period_window` | The period the month counters are read from. |

### Organization

| Method | Path | Purpose |
|---|---|---|
| `GET`, `PATCH`, `DELETE` | `/api/v1/orgs/{org_id}` | Read, update, or delete the organization. |
| `GET` | `/api/v1/orgs/{org_id}/members` | List members. |
| `PATCH` | `/api/v1/orgs/{org_id}/members/{member_id}` | Change a member's role. |
| `DELETE` | `/api/v1/orgs/{org_id}/members/{member_id}` | Remove a member. |
| `GET` | `/api/v1/orgs/{org_id}/invites` | List invites. |
| `POST` | `/api/v1/orgs/{org_id}/invites` | Invite a member. |
| `DELETE` | `/api/v1/orgs/{org_id}/invites/{invite_id}` | Revoke an invite. |
| `POST` | `/api/v1/orgs/{org_id}/invites/{invite_id}/resend` | Resend the invite email. |
| `GET` | `/api/v1/invites/{token}` | Public invite details. |
| `POST` | `/api/v1/invites/{token}/accept` | Accept an invite. |
| `POST` | `/api/v1/invites/{token}/decline` | Decline an invite. |

### API keys

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/orgs/{org_id}/api-keys` | List keys. |
| `POST` | `/api/v1/orgs/{org_id}/api-keys` | Mint a key. |
| `DELETE` | `/api/v1/orgs/{org_id}/api-keys/{key_id}` | Revoke a key. |
| `POST` | `/api/v1/orgs/{org_id}/api-keys/{key_id}/rotate` | Rotate the signing secret in place. |
| `GET` | `/api/v1/workflows/{workflow_id}/api-keys` | List the keys bound to one workflow. |

The raw key and the signing secret are returned once, at mint time. Store
them at once.

### Alerts

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/orgs/{org_id}/alerts` | List active alerts. |
| `POST` | `/api/v1/orgs/{org_id}/alerts/{alert_id}/dismiss` | Dismiss one alert. |
| `POST` | `/api/v1/orgs/{org_id}/alerts/dismiss-all` | Dismiss every alert. |
| `GET`, `POST` | `/api/v1/orgs/{org_id}/alert-channels` | List or create alert channels. |
| `GET`, `PATCH` | `/api/v1/orgs/{org_id}/notification-settings` | Per-user notification settings. |

### Auth

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/auth/register` | Create an account. Returns an API key and a signing secret. |
| `POST` | `/api/v1/auth/login` | Exchange email and password for a session token. |
| `POST` | `/api/v1/auth/verify` | Verify an API key and return the credential bundle. |
| `POST` | `/api/v1/auth/verify-email` | Confirm an email address. |
| `POST` | `/api/v1/auth/forgot-password` | Start a password reset. |
| `POST` | `/api/v1/auth/reset-password` | Finish a password reset. |
| `GET` | `/api/v1/auth/me` | The signed-in user. |
| `DELETE` | `/api/v1/auth/session` | Revoke the session. |

### Health

The health endpoints sit on the gateway's top-level router. They are not
under `/api/v1`. They answer `200` when healthy and `503` otherwise, with a
body listing each dependency.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health/live` | Liveness — the process accepts connections. |
| `GET` | `/health/ready` | Readiness — the dependencies are reachable. |
| `GET` | `/health/startup` | Startup — `200` once migrations finish, `503` while booting. |
| `GET` | `/health` | Alias for `/health/live`. |
| `GET` | `/healthz` | Alias for `/health/live`. |

## Capabilities

`GET /api/v1/capabilities` reports the wire contract the gateway supports.

| Field | Type | Notes |
|---|---|---|
| `min_protocol_version` | number | The oldest protocol version the gateway accepts. |
| `max_protocol_version` | number | The newest protocol version the gateway accepts. |
| `sdk_min_version` | string | The SDK version the gateway recommends. |
| `server_version` | string | The gateway release tag. |
| `capabilities` | object | The feature flags, nested under this key. |

The SDK probes this endpoint during `init()` and logs a warning when the
version the SDK sends falls outside the range the gateway accepts. The probe is
advisory: `init()` does not fail on a version mismatch.

## WebSocket control plane

`WS /ws/control/{organization_id}` streams control-plane events to a
connected SDK. The `{organization_id}` comes from the credential bundle, so the
SDK derives the URL on its own.

Server → client message types: `initial_state`, `state_change`,
`policy_invalidated`, `key_rotated`, `resync_required`, `error`, `pong`,
`approval_resolved`, `subscribed`.

Client → server message types: `ack`.

The SDK reads the workflow state from the socket. When the socket is
unavailable, the SDK falls back to polling `GET /api/v1/status/{workflow_id}`.

See [Control plane](../concepts/control-plane.md) for the reaction matrix.

## Example

The dashboard endpoints take a session token. The SDK endpoints take an API
key.

```bash title="shell"
TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
ORG_ID=8a3b1c7d-...

curl -X POST "https://api.nullrun.io/api/v1/orgs/$ORG_ID/workflows" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "production-bot",
    "external_id": "production-bot",
    "budget_cents": 5000
  }'
```

```bash title="shell"
curl "https://api.nullrun.io/api/v1/orgs/$ORG_ID/status" \
  -H "Authorization: Bearer $TOKEN"
```

## Errors

Every error response carries a machine-readable code. See
[Error codes](errors.md) for the gateway slugs, the enforcement codes, and the
SDK exception hierarchy.

## See also

- [Error codes](errors.md)
- [SDK API](sdk-api.md)
- [Control plane](../concepts/control-plane.md)
- [Budgets](../concepts/budgets.md)
