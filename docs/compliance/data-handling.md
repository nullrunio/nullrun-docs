---
title: Data handling & vendor review
maturity: stable
description: What data NULLRUN transmits, stores, where it is hosted, who can access it, and how it is deleted — for vendor security and compliance reviews.
---

# Data handling & vendor review

A consolidated response to the standard vendor-risk questionnaire, written
for an employee assessing NULLRUN as a vendor. Every value below is
anchored to backend code with `file:line` citations; rows marked
**Not attested** are honest gaps — the code does not document them.

This page is the load-bearing complement to the
[Compliance overview](index.md), the
[Geo restrictions](geo-restrictions.md) and
[Sanctions screening](sanctions-screening.md) pages. Those explain
*what NULLRUN enforces*; this page explains *what NULLRUN does with the
data it sees*.

**Reading conventions.** `[V]` = verified constant in source · `[D]` =
derived/inferred from code + ADR · `[N]` = not attested in repo.

## At-a-glance

| Question | Answer | Evidence |
|---|---|---|
| What does the SDK send? | Tool name, cost estimate, optional typed `business_impact`, optional `action_digest` (SHA-256 of canonical payload). | [§1 Data transmitted](#1-data-transmitted) |
| What does the backend store in Postgres? | Org / user / key / workflow / policy / approval / cost / audit rows. `audit_events` is **immutable** (4-layer defence). | [§2 Data stored](#2-data-stored-postgres) |
| What does the backend store in Redis? | Period cost counters, execution bindings, rate-limit buckets, session indexes, chain state. **No PII.** | [§3 Data stored](#3-data-stored-redis) |
| Where is it hosted? | DigitalOcean (US with EU regions). Self-hosted Postgres + Redis in Docker on a single VPS. | [§4 Hosting](#4-hosting--placement) |
| Who can access production data? | Owners / Admins / Operators / Viewers (4-level RBAC). SSH to prod only via allowlisted `vps` wrapper. | [§5 Access controls](#5-access-controls) |
| How is it encrypted? | TLS 1.2/1.3 edge, pgcrypto column-level for Slack OAuth tokens, HMAC-SHA256 for request signing, audit-export sidecar signing. | [§6 Encryption](#6-encryption) |
| Which third parties see data? | DigitalOcean, Brevo (DE), Polar (SE), Slack, GitHub, Google. Listed at `/api/v1/subprocessors`. | [§7 Sub-processors](#7-sub-processors) |
| How is data deleted? | Soft-delete with 60-day grace; hard purge via `purge_organization_data`; two-phase revoke for API keys. | [§8 Deletion](#8-deletion) |
| Where physically is data? | Region selectable at signup (EU or US). Single-region deployment. | [§9 Residency](#9-data-residency--sovereignty) |
| What's the compliance posture? | DPA available at `/api/v1/orgs/{org}/dpa`. No SOC 2 / ISO 27001 / HIPAA attestation in repo. | [§10 Compliance](#10-compliance-posture) |

## 1. Data transmitted

### 1.1 SDK → backend `/api/v1/gate`

Wire schema (`backend/src/proxy/http/gate/schemas.rs`):

| Field | Source | Notes |
|---|---|---|
| `execution_id` | SDK-supplied | Server **mints a UUIDv7** and echoes it back (`gate.rs`). Client-supplied IDs are not honoured for ownership — see ADR-003. |
| `trace_id`, `tool`, `mode`, `operation_id` | SDK-supplied | Standard envelope. |
| `business_impact {Money{direction, amount_minor, currency}}` | SDK-supplied | Optional; only required for typed approval rules. |
| `action_digest` | SDK-supplied | SHA-256 hex of canonicalised payload. Verified at `/execute` time per ADR-006. |
| `tool_params` | SDK-supplied | Optional JSON map. ToolParamsExtractor auto-attached since SDK 0.18.1. |
| `workflow_id`, `parent_execution_id` | SDK-supplied | Body `workflow_id` MUST match authenticated key's `workflow_id`, else `400 WORKFLOW_ID_BODY_MISMATCH` (WF-ID-01). |

**Org-mismatch guard (IDOR, P0-01):** body `organization_id` must match
authenticated context. Mismatch returns `OrgMismatch` block
(`gate.rs`).

**No email / no actor name** is sent by the SDK.

### 1.2 SDK → backend `/api/v1/track`

`TrackRequestRaw` (`backend/src/proxy/handlers.rs`): `event_id`,
`workflow_id` (required), `tokens`, `cost_cents` (accepted int/float/string
but **not trusted for enforcement** — server overwrites via 5%-delta rule;
"don't trust client-supplied execution_id or cost_cents" — CLAUDE.md
invariant), `tool_name`, `is_retry`, `operation_name`, `client_created_at`,
`input_tokens`, `output_tokens`, `agent_id`, `environment`, `agent_type`,
`reservation_id`, `reserved_cost_cents`, `provider`, `model`, `execution_id`,
`type_` (`llm_call`/`tool_call`/`span_start`/`span_end`), `trace_id`,
`span_id`, `parent_trace_id`, `metadata`, `parent_span_id`, `depth`,
`fn_name`, `error`, `idempotency_key`, `latency_ms`, `cost_source`,
`attempt_index`, `cache_read_tokens`, `cache_write_tokens`,
`reasoning_tokens`, `tool_names[]`, `finish_reason`.

### 1.3 Backend → SDK gate response

`backend/src/proxy/http/gate/schemas.rs`: `decision`,
`decision_source`, `explanation`, `approval_id`,
`approval_timeout_seconds`, server-minted `execution_id`,
`action_digest` echo, `policy_hash` (reserved), `idempotent_replayed: bool`.

**PII in gate responses:** decision/explanation text + approval IDs only.
No email, no org name, no actor identifier echoed. `[V]`

### 1.4 Backend ↔ upstream LLM provider

- `ProxyRequest` / `ProxyResponse` types and `proxy_handler` /
  `streaming_proxy_handler` exist at `backend/src/proxy/http/proxy.rs`.
- Provider enum covers OpenAI / Anthropic / Google / Azure (`provider/mod.rs`).
- **The route is NOT wired into the live router** — NULLRUN does not
  currently proxy LLM calls. The SDK talks to providers directly with
  the customer's own API keys. `[D]`
- **Vault invariant:** SDK never sees raw provider API keys; credentials
  would be resolved server-side. Per `backend/src/security/vault.rs`.

### 1.5 WebSocket control plane

- `WS_HMAC_MAX_AGE_SECONDS = 300` — replay window.
- HMAC-SHA256 over canonical JSON (sorted keys, no whitespace), keyed
  by per-API-key secret.
- Wire is signed; the receiver verifies against
  `bytes::from_hex(signed_payload)` — never against full wire bytes.
- Source: `backend/src/proxy/http/ws_control.rs`. `[V]`

### 1.6 Webhooks received

| Webhook | Verification | Source |
|---|---|---|
| **Polar** (billing) | HMAC-SHA256 verified BEFORE any processing. Accepts Standard Webhooks headers (`webhook-id`, `webhook-timestamp`, `webhook-signature: v1,<base64>`) and legacy `polar-signature: t=…,v1=…`. Sandbox bypass removed (2026 audit). | `backend/src/proxy/http/webhooks.rs` |
| **Slack events** | Signing-secret validation; bot tokens stored via pgcrypto encryption. | `slack_oauth.rs`, `crypto.rs` |
| **Geo-block** | IP allow/deny via MaxMind `GeoLite2-Country.mmdb` (operator-managed file). Fail-CLOSED (503) when DB unloadable. | `proxy/middleware/geo_block.rs` |

### 1.7 Email

- **Sub-processor:** Brevo (Sendinblue GmbH, **DE**). SMTP via
  `BREVO_SMTP_HOST` / `BREVO_SMTP_LOGIN` / `BREVO_SMTP_PASSWORD`.
  `backend/src/email.rs`. `[V]`
- **Email types:** invitation, invite-declined, 2FA recovery, password
  reset, verification, data-export-ready notification.
- **PII redaction in logs:** `EmailHash` Display renders a 12-char
  sha256 prefix, never plaintext. `backend/src/pii.rs`. `[V]`

## 2. Data stored — Postgres

| Table | Stored | Mutable? | Encryption at rest | Retention |
|---|---|---|---|---|
| `audit_events` | `id`, `organization_id`, `actor_id`, `action`, `event_type`, `decision`, `policy_id`, `policy_version`, `policy_hash`, `matched_rule`, `reason_code`, `execution_id`, `action_digest`, `tool_name`, `tool_version`, `tool_digest`, `metadata`, `content_hash`, `previous_hash`, `created_at` | **IMMUTABLE** | DB-level | Persistent until org purge (60-day grace) |
| `execution_records` | Per-execution outcome rows; joined on `execution_id` | Mutable | DB-level | Per `plan.history_days` (Lite=3, Scale=90) |
| `cost_events` | `cost_cents`, `cost_millicents`, `tokens`, `provider_reported_cost_cents`, `authoritative_cost_cents`, `cost_integrity` (provided/computed/estimated/provisional/reconciled), tool/model, trace/span/correlation IDs, agent/org IDs, `received_at`. Partitioned by month. | Mutable | DB-level | Env-driven `COST_EVENTS_RETENTION_DAYS`; defaults to per-plan `history_days` |
| `approvals` | Approval decisions, `decided_by_kind` (user / system_expiry / unknown per ADR-043) | Mutable (pending→approved/denied/expired/revoked) | DB-level | Pending GC'd by 5-s sweep worker |
| `organizations` | `id`, `name`, `slug`, `contact_email`, `plan`, `deleted_at`, `audit_purge_after` | Mutable; soft-delete via `deleted_at` with 60-day grace | DB-level | Hard-deleted by retention worker after grace |
| `users` | `id`, `email`, `display_name`, `password_hash` (Argon2), `role`, `default_organization_id`, `tombstoned_at`, `onboarding_completed_at` | Mutable; tombstone via `tombstoned_at` | DB-level | Persistent until org cascade |
| `organization_api_keys` | `id`, `name`, `key_prefix`, `key_suffix`, `key_hash` (SHA-256), `secret_key` (**HMAC plaintext — required for hot path**), `status` (active/rotating/revoked per ADR-010), `version`, `last_used_at`, `expires_at`, `scopes` | Mutable | DB-level | Persistent until org cascade |
| `sessions` | Bearer token store; session_token, user_id, org_id, expires_at | Mutable (revoke = DEL) | DB-level | 7-day TTL (Redis + PG) |
| `policies` | `id`, `scope` (Org/Workflow), `policy_type`, `enforcement_mode`, `budget_cents`, `max_overdraft_cents` | Mutable (soft-delete per ADR-047) | DB-level | Per `plan.history_days` |
| `audit_export_secrets` | Per-org HMAC secret for audit export signing | Mutable | DB-level | Persistent until org cascade |
| `workflows` | Workflow metadata, `state` (Normal/Flagged/Tripped/Paused/Killed), `budget_cents`, `archived_at`, `deleted_at` | Mutable | DB-level | Persistent |

### Audit-events immutability — 4-layer defence-in-depth

This is the SOC2 control surface:

1. Row-level `BEFORE UPDATE / DELETE` triggers raise `P0001`
   unconditionally. `db/mod.rs` (migration 149).
2. DDL event trigger `prevent_audit_ddl` blocks `ALTER / CREATE / DROP`
   on `audit_events` and `audit_exports`.
3. `REVOKE DELETE / TRUNCATE` on `audit_exports` from app role.
4. `ENABLE ALWAYS TRIGGER` hardening (migration 344, 2026-09-18) closes
   the `session_replication_role = 'replica'` bypass. **Closes
   DEF-PENTEST-001 P0** discovered in the 2026-09-18 internal pentest.
   `db/mod.rs`.

### Column-level encryption

`backend/src/crypto.rs` provides `encrypt_to_hex` /
`decrypt_from_hex` using pgcrypto AES. Used today for **Slack OAuth bot
tokens** (`slack_oauth.rs`). Threat model: stolen disk image OR
read-only DB dump yields ciphertext; plaintext requires DB +
`APP_ENCRYPTION_KEY`.

## 3. Data stored — Redis

| Key pattern | Purpose | PII | TTL | Source |
|---|---|---|---|---|
| `bp:{ts}:cost_cents` | Period-bound budget counter (cents). **Authoritative for enforcement.** | No (integer only) | `period_end_ts - now()`, capped `PERIOD_BUDGET = 35d` | `redis/mod.rs` |
| `bp:{ts}:executions` | Period-bound execution rate counter | No | Same TTL | `:362-368` |
| `execution:{execution_id}` | Hash binding (org_id, api_key_id). Anti-replay for `/track`, `/heartbeat` | No | `EXECUTION_BINDING = 24h` | `:283-291` |
| `rate_limit:{org_id}:{minute}` | Per-org rate-limit counter | No | `RATE_LIMIT = 120s` | `:45-48` |
| `rate_limit:gate:{key_id}:{minute}` | Per-API-key rate-limit counter on `/gate` | No | 120s | `:80-87` |
| `rl:tokens:{api_key_id}`, `rl:refill:{api_key_id}` | Token-bucket rate-limit state | No | 2× window | `:50-78` |
| `circuit_state:{org_id}:{wf_id}` | Workflow circuit-breaker state | No | `CIRCUIT_STATE = 3600s` | `:36-43` |
| `approval_request:{request_id}` | Approval pending metadata | No | `APPROVAL_REQUEST = 300s` | `:88-92` |
| `budget:reserved:{org_id}:{execution_id}` | Per-execution reservation | No | `authorization_deadline + 30s` (floor 60s, ceiling 24h) | `:162-165` |
| `pending_2fa:{token_key}` + `pending_2fa_user:{user_id}` | 2FA challenge (Redis-resident since GROWTH-4) | user_id only | `PENDING_2FA = 300s` | `:240-260` |
| `recovery_2fa:{token}` + `recovery_2fa_user:{user_id}` | OAuth 2FA-disable recovery token | user_id only | `RECOVERY_2FA = 24h` | `:262-281` |
| `in_flight:{org_id}:{api_key_id}` | In-flight counter for two-phase revoke drain (ADR-010) | No | 300s (KEEPTTL on decrement) | `:310-324` |
| `chain:{org_id}:{chain_id}` | Chain state-machine hash | No | `CHAIN_IDLE = 300s` | `:326-342` |
| `audit_hash:{organization_id}` | Last event's `content_hash` for chain fast-path | No | No TTL (cleanup-on-delete) | `:236-240` |
| `session:{token}` | Session token → user lookup | user_id | 7d (`SESSION_MAX_AGE_SECS`) | `auth/cookies.rs` |

**No PII** is stored in any of the above keys. Token keys, user indexes,
and approval metadata carry only opaque IDs (UUIDs).

## 4. Hosting & placement

| Layer | Provider / location | Source |
|---|---|---|
| **Cloud** | DigitalOcean LLC (US with EU regions). VPS at `68.183.71.186`, user `deploy-nullrun` | `infra/docker-compose.prod.yml`; `CLAUDE.md` VPS section |
| **Postgres** | Self-hosted Docker container on the VPS. App role `breaker_app`; pgcrypto extension | `infra/docker-compose.prod.yml` |
| **Redis** | Self-hosted Docker container on the same VPS. AOF + RDB backup via `infra/backup.sh` | same |
| **Object storage** | S3-compatible (`BACKUP_S3_BUCKET` env-gated). Compatible with DO Spaces via `S3_ENDPOINT` override. Audit export + backup upload | `backend/src/storage/s3.rs` |
| **Container orchestration** | Docker Compose on a single VPS. Blue-green deploys mandatory for budget/auth paths; rolling OK for bug fixes / docs / SDK-only | `CLAUDE.md` Deploy & ops |
| **CDN / edge** | None. nginx on the VPS terminates TLS and reverse-proxies. Direct origin exposure | `infra/nginx/nginx-vps.conf` |
| **DNS** | nginx virtual hosts: `nullrun.io`, `www.nullrun.io`, `api.nullrun.io`. DNS provider not in repo | `[D]` |

### Container hardening

Per `infra/docker-compose.prod.yml`:

- `read_only: true` root FS
- `cap_drop: [ALL]`
- `no-new-privileges: true`
- `tmpfs /tmp` (noexec / nosuid / nodev, 100M)
- Bind-mounted screening data (OFAC + GeoLite2)

### TLS

- `ssl_protocols TLSv1.2 TLSv1.3;` (no SSLv3 / TLS 1.0 / 1.1)
- Mozilla "intermediate" cipher list (2024)
- HSTS preload candidate, `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- Certbot-managed Let's Encrypt at `/etc/letsencrypt/live/nullrun.io/`
- Source: `infra/nginx/nginx-vps.conf`. `[V]`

## 5. Access controls

### 5.1 RBAC

4-level hierarchy. `backend/src/auth/rbac.rs`:

| Role | Level | Used for |
|---|---|---|
| Viewer | 0 | Read-only dashboard |
| Operator | 1 | Operator-tier mutations (kill / pause workflows, decide approvals). **Runtime-tier only** — does not exist in storage |
| Admin | 2 | Org management, member management |
| Owner | 3 | Org deletion, billing changes, ownership transfer |

**Storage-layer role** (`OrganizationRole`) is parallel but not
isomorphic: `Viewer / Member / Admin / Owner`. Conversion documented
at `auth/rbac.rs`.

**Machine API keys** carry `role = None` denotationally (ADR-053).
RBAC-protected mutations require user-bound key
(`RbacError::UserBindingRequired` at `:117-120`).

**Platform admin** additionally requires TOTP enabled + Owner role
(`auth/admin.rs`); fail-CLOSED on TOTP-lookup error.

### 5.2 Auth methods

| Method | Wire | Source |
|---|---|---|
| Session cookies (browser) | `__Host-nullrun_session` (prod) / `nullrun_session` (dev). `__Host-` prefix requires Secure + Path=/ + no Domain. HttpOnly, SameSite=Lax, 7-day TTL. Defaults fail-CLOSED to prod (not dev) per 2026-07-15 hardening | `auth/cookies.rs` |
| API keys (machine) | `nr_live_*` prefix; HMAC-SHA256 over `timestamp + ":" + api_key + ":" + body_hash`. `HmacKeyStore` supports versioned rotation + Redis pub/sub fan-out (`nullrun:hmac:keys` channel). Constant-time comparison via `subtle::ConstantTimeEq` | `backend/src/auth/hmac.rs+` |
| OAuth (identity) | GitHub + Google OAuth 2.0 redirect | `auth/github.rs`, `google.rs` |
| SSO | SAML/SSO labelled `DISABLED_IN_PROD` in repo instructions (`CLAUDE.md` "OAuth") | `[D]` |

### 5.3 2FA

- **TOTP RFC 4226:** 6 digits, 30s period, 160-bit secret, 10 recovery
  codes on enable. Setup/verify/disable/recovery-codes endpoints under
  `/api/v1/auth/2fa/*`.
- **Platform admin endpoints** require TOTP-enabled user.
- **Recovery tokens** for OAuth users disabling 2FA: 24h TTL via
  `recovery_2fa:{token}` (Redis); single-use `GETDEL`.
- Source: `backend/src/proxy/http/user_security.rs`. `[V]`

### 5.4 API key scopes

- `SCOPE_ADMIN` required for non-Owner admins on `/admin/*` paths
  (`backend/src/auth/admin.rs`).
- Workflow binding: API keys carry `workflow_id` (Phase 139); body
  `workflow_id` MUST match authenticated key's workflow, else
  `400 WORKFLOW_ID_BODY_MISMATCH` (WF-ID-01).
- Status: `active` / `rotating` / `revoked` per ADR-010.

### 5.5 Audit log access

- **Plan-gated:** `plan.features.audit_log` controls read access; Lite
  plan has `audit_log: false` (no customer access).
- **RLS:** Migration 347 (2026-09-21) added per-org SELECT policy on
  `audit_events`. Every raw `pool.begin()` reader MUST set
  `app.current_org_id` GUC.
- **Plan tier retention:** `plan.history_days` controls
  `UserVisibleHistory` retention; `-1` = unlimited
  (`audit/kind.rs`).

### 5.6 Operator access to production

- SSH only via `vps` wrapper (`infra/scripts/vps`). Allowlisted
  subcommands: `redis-cli`, `psql`, `journalctl -u <unit>`.
- **Blocked:** `printenv`, `docker inspect`, raw `cat` of `.env.prod`,
  mutating docker subcommands.
- Production creds sourced from GH Secret `ENVPROD_FILE`, atomic render
  by CI.

## 6. Encryption

| Layer | Mechanism | Source |
|---|---|---|
| **In transit — server edge** | TLS 1.2 / 1.3, Mozilla intermediate ciphers, HSTS preload candidate | `infra/nginx/nginx-vps.conf` |
| **In transit — WebSocket** | HMAC-SHA256 over canonical JSON, replay window 300 s | `ws_control.rs` |
| **At rest — Postgres (column)** | pgcrypto AES via `crypto::encrypt_to_hex` / `decrypt_from_hex`. Used for Slack OAuth bot tokens. Threat model: stolen DB dump + missing `APP_ENCRYPTION_KEY` = ciphertext | `crypto.rs` |
| **At rest — Postgres (disk)** | **Not attested** in repo; relies on DigitalOcean droplet disk encryption | `[N]` |
| **At rest — Redis** | **Not attested** in repo; bind-mounted AOF/RDB volumes rely on host disk encryption | `[N]` |
| **At rest — S3 / object storage** | `S3Client` writes via `BACKUP_S3_BUCKET`. Bucket-side encryption (SSE-S3 / SSE-KMS) configuration is **not exposed in repo** | `[D]` |
| **KMS / key management** | `APP_ENCRYPTION_KEY` env var drives pgcrypto AES. No AWS KMS / GCP KMS / HashiCorp Vault integration visible. Rotation requires manual runbook (breaks 2FA + Slack per `CLAUDE.md`) | `[D]` |
| **HMAC for request signing** | `NULLRUN_GATEWAY_SIGNING_KEY` (≥32 bytes, never auto-generated), used for HMAC-SHA256 of gate/execute/track bodies. `config.rs` | `[V]` |
| **API keys at rest** | `key_hash` SHA-256 stored; `secret_key` plaintext stored (HMAC hot-path requirement). Key prefix / suffix surfaced for UI display | `[V]` |
| **Cookie security flags** | `__Host-` prefix, Secure, HttpOnly (session), SameSite=Lax, Path=/, 7-day Max-Age. CSRF cookie NOT HttpOnly (SPA reads it). Production = fail-CLOSED default | `auth/cookies.rs` |
| **Audit export signing** | Per-export HMAC-SHA256 sidecar via `NULLRUN_AUDIT_EXPORT_SECRET` (or per-org secret). Fail-CLOSED in prod (no dev fallback) | `proxy/http/audit.rs` |

## 7. Sub-processors

Canonical list (`backend/src/proxy/http/dpa.rs`) and
`SUBPROCESSOR_LIST_VERSION = 2026-06-25`. Public endpoint:
`GET /api/v1/subprocessors` (ETag-cached).

| Sub-processor | Role | Country | Transfer mechanism | Since | Opt-in |
|---|---|---|---|---|---|
| **DigitalOcean LLC** | Hosting (PG, Redis, app servers) | US (EU regions) | EU SCCs (Module 2/3) for US-region; EU residency available | 2024-01-01 | No |
| **Brevo (Sendinblue GmbH)** | Transactional email | DE (Germany) | Adequacy decision (EU) | 2024-01-01 | No |
| **Polar.sh (Polar Software Sweden AB)** | Payment, subscriptions, tax (merchant of record) | SE (Sweden) | Adequacy decision (EU) | 2024-01-01 | No |
| **Slack Technologies, LLC** | Alert delivery (OAuth) | US | EU SCCs (Module 3) | 2024-06-01 | Yes |
| **GitHub Inc.** | OAuth identity provider | US | EU SCCs (Module 3) | 2024-01-01 | Yes |
| **Google LLC** | OAuth identity provider | US | EU SCCs (Module 3) | 2024-01-01 | Yes |

**MaxMind** (geo-IP): GeoLite2-Country `.mmdb` self-hosted in
container; no live API calls.

**LLM providers:** `/api/v1/proxy*` route types exist
(`backend/src/proxy/http/proxy.rs`) but the route is NOT wired into the
live router. NULLRUN does not currently proxy calls to OpenAI / Anthropic
/ Google / Azure. The SDK talks to providers directly with its own keys.

**Analytics / observability vendors:** Self-hosted stack — Prometheus +
Grafana + alertmanager + vector + Loki (all in `infra/observability/`).
No Datadog / Sentry / Segment / Mixpanel / Amplitude references in
backend.

**Backup storage:** S3-compatible (`BACKUP_S3_BUCKET` env-gated); config
tar encrypted with GPG before upload.

## 8. Deletion

### 8.1 Organization deletion

**Soft-delete path** (`db/mod.rs-…`):

- `UPDATE organizations SET deleted_at = NOW(), audit_purge_after = NOW() + 60 days`
- Audit rows **intentionally retained** during grace for SOC2 immutability.
- Owner can restore via `/restore` endpoint (clears both columns).
- Handler returns `409 AUDIT_HISTORY_RETAINED` with `grace_period_days: 60`
  when audit history exists.
- Child-table cascade (api_keys, policies, workflows, invites) updated
  in the same tx.

**Hard purge path** (`purge_soft_deleted_org`, `db/mod.rs-…`):

- Runs hourly after `audit_purge_after`.
- Calls `purge_organization_data` (scrubs `audit_events`,
  `decision_history`, `cost_events`, `billing_events`).
- Source-pinned by `audit_immutability_bypass_pin_tests.rs`.
- `DELETE FROM organizations`.

**Audit immutability bypass:** within the same tx, `DISABLE TRIGGER
trg_reject_audit_event_update + trg_reject_audit_event_delete`,
`DELETE` rows, `ENABLE ALWAYS TRIGGER` (re-hardens to
`tgenabled = 'A'`). Pre-fix used function name as trigger name — bug
fixed 2026-09-18 per migration 344.

### 8.2 User account deletion

`DELETE /api/v1/auth/account`. Three cases per ADR-048
(`docs/adr/ADR-048-account-delete-ownership-decision-cascade.md`):

| Case | Behaviour |
|---|---|
| Sole-owner sole-member org | Auto soft-deleted (no decision required) |
| Co-member org, decision = `delete_and_notify` | Soft-delete + fail-CLOSED revoke of all co-member sessions |
| Co-member org, decision = `transfer { to_user_id }` | Promote new owner, no delete |

Wire-additive: `ownership_decisions: HashMap<Uuid, OwnershipDecision>`.
Fail-CLOSED if Redis hiccup on session revoke (503). `[V]`

### 8.3 API key revocation — two-phase with in-flight drain

Per ADR-010 (`docs/adr/ADR-010-api-key-lifecycle-revoke-drain.md`):

1. **Phase 1:** transition to `rotating`; `pg_notify` fires on all pods;
   `ApiKeyDenyList` short-circuits warm-cache hits.
2. **Phase 2:** drain supervisor polls
   `in_flight:{org_id}:{api_key_id}` counter until 0 or timeout.
3. **Phase 3:** status → `revoked`. Counter does NOT return
   (preserved for audit / reconciliation).

TTL of deny-list = 2× auth_cache TTL = 600 s.
Source: `backend/src/redis/in_flight.rs`,
`proxy/auth_lifecycle/{listener,deny_list,mod}.rs`.

### 8.4 GDPR / right-to-erasure

| Right | Implementation | Source |
|---|---|---|
| **Art. 15 — right of access** | `POST /api/v1/auth/data-export` per-user job+worker pattern. 7-day download TTL, 100k-record cap per section | `data_export.rs` |
| **Art. 17 — right to erasure** | `purge_organization_data` scrubs tenant-scoped data; triggered automatically 60 days after org soft-delete. No manual kickoff path documented for self-serve | `[V]` |
| **Audit retention on erasure** | Audit rows physically deleted when org is purged (after 60-day grace). Pre-purge, retained even on soft-delete (intentional — SOC2) | `[V]` |
| **Drift guard** | A-C-2 pin test prevents payloads from accumulating PII (e.g., email) that would later need GDPR erasure to scrub | `audit/drift_tests.rs` |

## 9. Data residency & sovereignty

- **Physical storage:** DigitalOcean droplets. Region selectable at
  signup: customers who pick EU get EU-resident Postgres / Redis.
- **Cross-region replication:** **Not attested** in repo. Single-region
  deployment posture.
- **Cross-border transfers** (per `dpa.rs`):
  - US sub-processors (DO US regions, Slack, GitHub, Google) →
    **EU SCCs (Decision 2021/914) Module 2/3**.
  - EU sub-processors (Brevo DE, Polar SE, DO EU) → adequacy decision
    (no SCC needed).
- **In-product region enforcement:** customers who select EU residency
  at signup have data physically in EU. Wire transfers: EU SCCs for US
  endpoints; otherwise data never leaves EU. `[D]`
- **Customer-side region selection:** stated in `dpa.rs`
  ("EU residency available (default for customers who select the EU
  region)"); the signup-time selection mechanism is not directly exposed
  in the visible code. `[D]`

## 10. Compliance posture

| Item | Status | Source |
|---|---|---|
| **DPA** | Available. `GET /api/v1/orgs/{org}/dpa` returns accepted-version + history; `POST /api/v1/orgs/{org}/dpa/accept` is idempotent on `(org_id, dpa_version)`. Acceptance recorded as `compliance.dpa.accepted` audit row. | `backend/src/proxy/http/dpa.rs+` |
| **DPA text version** | `2026-09-16`. Sub-processor list snapshot: `2026-06-25`. | same |
| **Sub-processor endpoint** | `GET /api/v1/subprocessors` (public, ETag-cached) | `dpa.rs` |
| **GDPR Art. 15** | Per-user export implemented (`data_export.rs`) | `[V]` |
| **GDPR Art. 17** | Right-to-erasure via `purge_organization_data` (60-day grace) | `[V]` |
| **SOC 2** | Code references "SOC2 immutability" repeatedly (`db/mod.rs`, `:22334`). The `audit_events` immutability guarantee is the SOC2 control surface. **No SOC 2 Type II report attestation in repo.** | `[D]` |
| **ISO 27001** | **Not claimed** in any file or doc found | `[N]` |
| **HIPAA** | **Not claimed** in any file or doc found | `[N]` |
| **CCPA** | **Not claimed** in any file or doc found | `[N]` |
| **Privacy policy URL** | Referenced via `/dpa` and `/privacy` pages but exact URL not in this repo (lives in nullrun-docs / frontend) | `[N]` |
| **Audit export** | HMAC-signed JSONL / S3 download via `audit_exports` table + worker | `[V]` |

## 11. Breach & incident response

| Item | Status | Source |
|---|---|---|
| **Alerting surface** | Self-hosted **Prometheus alertmanager** + Slack (per-channel via OAuth). Alert rules in `infra/alerting/prometheus-alerts.yaml` (track error rate >1% for 2m, P95 >200ms for 5m, P99 >500ms for 3m, out-of-order events, etc.). PagerDuty REMOVED (migration 300). | `[V]` |
| **Alert channels** | `alert_channels.rs` supports `Webhook` and `Slack` discriminated union. Email channel REMOVED (migration 292). PagerDuty / Discord REMOVED (migration 300). | `[V]` |
| **Runbooks** | 30+ topic-specific runbooks in `docs/runbooks/` (track-error-rate, audit-drain-stuck, outbox-dlq, period-rollover-decision, envprod-leak, billing-drift, etc.) | `[V]` |
| **Status page** | **Not referenced** in repo | `[N]` |
| **Breach-notification SLA** | **Not documented** in repo | `[N]` |
| **On-call rotation** | **Not documented** in repo | `[N]` |

## 12. Penetration testing

| Item | Status |
|---|---|
| **Internal pentest** | "Comprehensive pentest profile plan" exists at `explotarory testing/NULLRUN_comprehensive_pentest_profile_plan.md`. RUN_ID-scoped phases (`FULLSESSION-20260918T1430-pentest-phase1-*`, `phase2-*`, `phase3-*`) executed 2026-09-18 against local docker stack |
| **Findings materialised in code** | Migration 344 (`tgenabled = 'A'` hardening) closed **DEF-PENTEST-001 P0** — audit-event immutability bypass via `session_replication_role='replica'`. `db/mod.rs` |
| **External pentest report** | **Not in repo** |
| **Bug bounty program** | **Not advertised** in repo |

## 13. Other load-bearing controls

- **HMAC required for all gate calls.** `NULLRUN_HMAC_REQUIRED=true`
  enforced in production. Missing / invalid → reject before enforcement.
- **Protocol header required.** `X-NULLRUN-PROTOCOL` on every gate
  request; `/health` returns min/max (currently min=2, max=4,
  current=4). `protocol.rs`.
- **Fail-CLOSED on enforcement paths.** Budget path (Redis down → 402
  `REDIS_UNAVAILABLE`); geo-block (MaxMind unloadable → 503). Per
  `CLAUDE.md` "Five load-bearing invariants".
- **IDOR guards.** Body org mismatch (P0-01), `workflow_id`
  body-vs-key mismatch (WF-ID-01), parent execution cross-org rejection.
- **CSRF double-submit** for browser POSTs; `Authorization: Bearer`
  bypasses for API path. SHA-256-then-constant-time comparison.
- **PII redaction** for log lines (`backend/src/pii.rs`).
- **Secret scanning pre-commit.** trufflehog (~700 provider sigs) +
  gitleaks (NullRun-specific key shapes). 500 KB max file size.
  `.pre-commit-config.yaml` enforces.

## Honest gaps

These items are either not documented in the codebase or rely on
third-party evidence. They are the questions a vendor reviewer should
follow up on:

### Not attested in repo `[N]`

1. **SOC 2 / ISO 27001 / HIPAA / CCPA formal attestations.** No
   certificates or reports in repo. The "SOC2 immutability" wording
   refers to a self-imposed control, not third-party certification.
2. **External penetration test report.** Only an internal pentest plan
   and journal exist.
3. **Bug bounty program.** Not advertised.
4. **Status page.** No reference to `status.nullrun.io` or similar.
5. **Public breach-notification SLA / DPA SLA.** Not documented in repo.
6. **Postgres tablespace / disk-level encryption at rest.** pgcrypto
   column-level encryption is used for Slack OAuth bot tokens;
   full-disk / tablespace encryption is not explicitly attested (relies
   on DigitalOcean droplet disk).
7. **Redis disk encryption.** AOF/RDB volumes are bind-mounted; no
   explicit encryption-at-rest on Redis noted.
8. **S3 / object-storage encryption settings.** `storage/s3.rs` is
   implemented; bucket-side encryption configuration (SSE-S3 / SSE-KMS)
   is not exposed in repo.
9. **Customer-side region selection mechanism.** The DPA wording ("EU
   residency available (default for customers who select the EU
   region)") references a signup-time choice; the wire path that
   records the customer's region preference was not located in this
   audit.
10. **DPA URL outside the BFF.** Frontend pages (`/dpa`, `/privacy`)
    live in nullrun-docs / frontend; this audit did not verify them.
11. **Cross-region replication / DR posture.** Single-region (one VPS)
    is the deployed topology. No documented failover.
12. **Privacy policy URL.** Not in this repo.

### Inferred from code, not direct attestation `[D]`

13. **Wire shapes for `/api/v1/proxy`.** `ProxyRequest` / `ProxyResponse`
    types are present and complete, but no live route registration was
    located. Marketing claim "we don't proxy your LLM calls" is
    consistent with code — but a future PR could wire it without
    changing types.
14. **`api.nullrun.io` TLS minimum version on SDK client side.** Repo
    enforces TLS 1.2/1.3 at the nginx edge; SDK-side enforcement (i.e.
    whether the SDK pins a min TLS) was not audited (lives in
    `nullrun-sdk-python`).
15. **KMS / key management.** `APP_ENCRYPTION_KEY` is an env var; no
    AWS KMS / GCP KMS / HashiCorp Vault integration visible. Key
    rotation requires manual runbook.
16. **Operator access logs / session recording.** Production SSH access
    path is documented (`vps` wrapper); no evidence of operator-action
    audit logging on the DB tier itself (beyond `audit_events` rows that
    customer code writes).
17. **API key scopes beyond admin.** `SCOPE_ADMIN` is the only named
    scope found. Granular scopes per workspace / operation were not
    enumerated in this audit.

## How to verify

Any of these numbers can drift between this page and the actual code.
When that happens, **the code wins**. To re-derive:

```bash
# From NULLRUN repo root
git grep -nE 'CREATE TABLE.*audit_events' backend/src/db/migrations/
git grep -nE 'BEFORE (UPDATE|DELETE)' backend/src/db/migrations/ | grep -i audit
git grep -nE 'trg_reject_audit_event' backend/src/db/
git grep -nE 'WEBHOOK_SIGNATURE_MAX_AGE_SECS' backend/src/billing/polar.rs
git grep -n 'SUBPROCESSOR_LIST_VERSION' backend/src/proxy/http/dpa.rs
git grep -n 'soft-delete\|deleted_at\|audit_purge_after' backend/src/db/mod.rs
```

## See also

- [Compliance overview](index.md)
- [Geo restrictions](geo-restrictions.md)
- [Sanctions screening](sanctions-screening.md)
- [Performance & limits](../operations/performance.md) — latency,
  failure-mode behaviour, timeouts
- [API keys](../concepts/api-keys.md) — HMAC, rotation, drain
- [Organization](../concepts/organization.md) — delete-org flow
- [Profile settings](../concepts/profile.md) — account delete flow
