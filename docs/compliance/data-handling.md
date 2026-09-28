---
title: Data handling & vendor review
maturity: stable
description: What data NULLRUN transmits, stores, where it is hosted, who can access it, and how it is deleted — for vendor security and compliance reviews.
---

# Data handling & vendor review

A consolidated response to the standard vendor-risk questionnaire, written
for an employee assessing NULLRUN as a vendor. Every value below reflects
the deployed product; rows marked **Not attested** are honest gaps — the
implementation does not document them.

This page is the load-bearing companion to the
[Compliance overview](index.md). That page gives the short version;
this one answers the vendor-risk questionnaire in full — *what NULLRUN
does with the data it sees*.

**Reading conventions.** `[V]` = verified · `[D]` = derived or inferred
· `[N]` = not attested.

## At-a-glance

| Question | Answer | Evidence |
|---|---|---|
| What does the SDK send? | Tool name, cost estimate, optional typed `business_impact`, optional `action_digest` (SHA-256 of canonical payload). | [§1 Data transmitted](#1-data-transmitted) |
| What does the backend store in Postgres? | Org / user / key / workflow / policy / approval / cost / audit rows. `audit_events` is **immutable** (4-layer defence). | [§2 Data stored](#2-data-stored-postgres) |
| What does the backend store in Redis? | Period cost counters, execution bindings, rate-limit buckets, session indexes, chain state. **No PII.** | [§3 Data stored](#3-data-stored-redis) |
| Where is it hosted? | DigitalOcean (US with EU regions). Self-hosted Postgres + Redis in Docker on a single VPS. | [§4 Hosting](#4-hosting-placement) |
| Who can access production data? | Owners / Admins / Operators / Viewers (4-level RBAC). SSH to prod only via allowlisted `vps` wrapper. | [§5 Access controls](#5-access-controls) |
| How is it encrypted? | TLS 1.2/1.3 edge, pgcrypto column-level for Slack OAuth tokens, HMAC-SHA256 for request signing, audit-export sidecar signing. | [§6 Encryption](#6-encryption) |
| Which third parties see data? | DigitalOcean, Brevo (DE), Polar (SE), Slack, GitHub, Google. Listed at `/api/v1/subprocessors`. | [§7 Sub-processors](#7-sub-processors) |
| How is data deleted? | Soft-delete with 60-day grace, then a hard purge of tenant data; two-phase revoke for API keys. | [§8 Deletion](#8-deletion) |
| Where physically is data? | Region selectable at signup (EU or US). Single-region deployment. | [§9 Residency](#9-data-residency-sovereignty) |
| What's the compliance posture? | DPA available at `/api/v1/orgs/{org}/dpa`. No SOC 2 / ISO 27001 / HIPAA attestation is available. | [§10 Compliance](#10-compliance-posture) |

## 1. Data transmitted

### 1.1 SDK → backend `/api/v1/gate`

Wire schema:

| Field | Source | Notes |
|---|---|---|
| `execution_id` | SDK-supplied | Server **mints a UUIDv7** and echoes it back. Client-supplied IDs are not honoured for ownership. |
| `trace_id`, `tool`, `mode`, `operation_id` | SDK-supplied | Standard envelope. |
| `business_impact {Money{direction, amount_minor, currency}}` | SDK-supplied | Optional; only required for typed approval rules. |
| `action_digest` | SDK-supplied | SHA-256 hex of canonicalised payload. Verified again at `/execute` time. |
| `tool_params` | SDK-supplied | Raw `kwargs` under `input_data.kwargs`; backend reads by `param_name` in ToolParameters approval rules. |
| `workflow_id`, `parent_execution_id` | SDK-supplied | Body `workflow_id` MUST match the authenticated key's `workflow_id`, else `400 WORKFLOW_ID_BODY_MISMATCH`. |

**Org-mismatch guard (IDOR):** the body `organization_id` must match the
authenticated context. A mismatch returns an `OrgMismatch` block.

**No email / no actor name** is sent by the SDK.

### 1.2 SDK → backend `/api/v1/track`

`TrackRequestRaw` carries `event_id`,
`workflow_id` (required), `tokens`, `cost_cents` (accepted int/float/string
but **not trusted for enforcement** — the server overwrites it via a
5%-delta rule: client-supplied `execution_id` and `cost_cents` are never
trusted), `tool_name`, `is_retry`, `operation_name`, `client_created_at`,
`input_tokens`, `output_tokens`, `agent_id`, `environment`, `agent_type`,
`reservation_id`, `reserved_cost_cents`, `provider`, `model`, `execution_id`,
`type_` (`llm_call`/`tool_call`/`span_start`/`span_end`), `trace_id`,
`span_id`, `parent_trace_id`, `metadata`, `parent_span_id`, `depth`,
`fn_name`, `error`, `idempotency_key`, `latency_ms`, `cost_source`,
`attempt_index`, `cache_read_tokens`, `cache_write_tokens`,
`reasoning_tokens`, `tool_names[]`, `finish_reason`.

### 1.3 Backend → SDK gate response

The gate response carries `decision`, `decision_source`,
`explanation`, `approval_id`,
`approval_timeout_seconds`, server-minted `execution_id`,
`action_digest` echo, `policy_hash` (reserved), `idempotent_replayed: bool`.

**PII in gate responses:** decision/explanation text + approval IDs only.
No email, no org name, no actor identifier echoed. `[V]`

### 1.4 Backend ↔ upstream LLM provider

- Provider types cover OpenAI / Anthropic / Google / Azure.
- **The proxy route is not wired into the live router** — NULLRUN does
  not proxy LLM calls. The SDK talks to providers directly with the
  customer's own API keys. `[D]`
- **Credential invariant:** the SDK never sees raw provider API keys;
  credentials are resolved server-side.

### 1.5 WebSocket control plane

- `WS_HMAC_MAX_AGE_SECONDS = 300` — replay window.
- HMAC-SHA256 over canonical JSON (sorted keys, no whitespace), keyed
  by per-API-key secret.
- The wire is signed; the receiver verifies the decoded signed payload
  — never the full wire bytes. `[V]`

### 1.6 Webhooks received

| Webhook | Verification |
|---|---|
| **Polar** (billing) | HMAC-SHA256 verified BEFORE any processing. Accepts Standard Webhooks headers (`webhook-id`, `webhook-timestamp`, `webhook-signature: v1,<base64>`) and the `polar-signature: t=…,v1=…` fallback. The sandbox environment bypasses verification; production does not. |
| **Slack events** | Signing-secret validation; bot tokens stored via pgcrypto encryption. |

### 1.7 Email

- **Sub-processor:** Brevo (Sendinblue GmbH, **DE**). SMTP via
  `BREVO_SMTP_HOST` / `BREVO_SMTP_LOGIN` / `BREVO_SMTP_PASSWORD`. `[V]`
- **Email types:** invitation, invite-declined, 2FA recovery, password
  reset, verification, data-export-ready notification.
- **PII redaction in logs:** email addresses render as a 12-char
  SHA-256 prefix, never plaintext. `[V]`

## 2. Data stored — Postgres

| Table | Stored | Mutable? | Encryption at rest | Retention |
|---|---|---|---|---|
| `audit_events` | `id`, `organization_id`, `actor_id`, `action`, `event_type`, `decision`, `policy_id`, `policy_version`, `policy_hash`, `matched_rule`, `reason_code`, `execution_id`, `action_digest`, `tool_name`, `tool_version`, `tool_digest`, `metadata`, `content_hash`, `previous_hash`, `created_at` | **IMMUTABLE** | DB-level | Persistent until org purge (60-day grace) |
| `execution_records` | Per-execution outcome rows; joined on `execution_id` | Mutable | DB-level | Per `plan.history_days` (Lite=3, Scale=90) |
| `cost_events` | `cost_cents`, `cost_millicents`, `tokens`, `provider_reported_cost_cents`, `authoritative_cost_cents`, `cost_integrity` (provided/computed/estimated/provisional/reconciled), tool/model, trace/span/correlation IDs, agent/org IDs, `received_at`. Partitioned by month. | Mutable | DB-level | Env-driven `COST_EVENTS_RETENTION_DAYS`; defaults to per-plan `history_days` |
| `approvals` | Approval decisions, `decided_by_kind` (user / system_expiry / unknown) | Mutable (pending→approved/denied/expired/revoked) | DB-level | Pending GC'd by 5-s sweep worker |
| `organizations` | `id`, `name`, `slug`, `contact_email`, `plan`, `deleted_at`, `audit_purge_after` | Mutable; soft-delete via `deleted_at` with 60-day grace | DB-level | Hard-deleted by retention worker after grace |
| `users` | `id`, `email`, `display_name`, `password_hash` (Argon2), `role`, `default_organization_id`, `tombstoned_at`, `onboarding_completed_at` | Mutable; tombstone via `tombstoned_at` | DB-level | Persistent until org cascade |
| `organization_api_keys` | `id`, `name`, `key_prefix`, `key_suffix`, `key_hash` (SHA-256), `secret_key` (**HMAC plaintext — required for hot path**), `status` (active/rotating/revoked), `version`, `last_used_at`, `expires_at`, `scopes` | Mutable | DB-level | Persistent until org cascade |
| `sessions` | Bearer token store; session_token, user_id, org_id, expires_at | Mutable (revoke = DEL) | DB-level | 7-day TTL (Redis + PG) |
| `policies` | `id`, `scope` (Org/Workflow), `policy_type`, `enforcement_mode`, `budget_cents`, `max_overdraft_cents` | Mutable (soft-delete) | DB-level | Per `plan.history_days` |
| `audit_export_secrets` | Per-org HMAC secret for audit export signing | Mutable | DB-level | Persistent until org cascade |
| `workflows` | Workflow metadata, `state` (Normal/Flagged/Tripped/Paused/Killed), `budget_cents`, `archived_at`, `deleted_at` | Mutable | DB-level | Persistent |

### Audit-events immutability — 4-layer defence-in-depth

This is the SOC2 control surface:

1. Row-level `BEFORE UPDATE / DELETE` triggers raise an error
   unconditionally.
2. A DDL event trigger blocks `ALTER / CREATE / DROP` on the audit
   event and audit export tables.
3. `DELETE` and `TRUNCATE` are revoked on the audit export table from
   the application role.
4. `ENABLE ALWAYS TRIGGER` hardening closes the
   `session_replication_role = 'replica'` bypass — an audit-event
   immutability bypass found during internal penetration testing.

### Column-level encryption

Column-level encryption uses pgcrypto AES. It is applied to **Slack
OAuth bot tokens**. Threat model: stolen disk image OR
read-only DB dump yields ciphertext; plaintext requires DB +
`APP_ENCRYPTION_KEY`.

## 3. Data stored — Redis

| Key pattern | Purpose | PII | TTL |
| --- | --- | --- | --- |
| `bp:{ts}:cost_cents` | Period-bound budget counter (cents). **Authoritative for enforcement.** | No (integer only) | `period_end_ts - now()`, capped `PERIOD_BUDGET = 35d` |
| `bp:{ts}:executions` | Period-bound execution rate counter | No | Same TTL |
| `execution:{execution_id}` | Hash binding (org_id, api_key_id). Anti-replay for `/track`, `/heartbeat` | No | `EXECUTION_BINDING = 24h` |
| `rate_limit:{org_id}:{minute}` | Per-org rate-limit counter | No | `RATE_LIMIT = 120s` |
| `rate_limit:gate:{key_id}:{minute}` | Per-API-key rate-limit counter on `/gate` | No | 120s |
| `rl:tokens:{api_key_id}`, `rl:refill:{api_key_id}` | Token-bucket rate-limit state | No | 2× window |
| `circuit_state:{org_id}:{wf_id}` | Workflow circuit-breaker state | No | `CIRCUIT_STATE = 3600s` |
| `approval_request:{request_id}` | Approval pending metadata | No | `APPROVAL_REQUEST = 300s` |
| `budget:reserved:{org_id}:{execution_id}` | Per-execution reservation | No | `authorization_deadline + 30s` (floor 60s, ceiling 24h) |
| `pending_2fa:{token_key}` + `pending_2fa_user:{user_id}` | 2FA challenge (Redis-resident) | user_id only |
| `recovery_2fa:{token}` + `recovery_2fa_user:{user_id}` | OAuth 2FA-disable recovery token | user_id only | `RECOVERY_2FA = 24h` |
| `in_flight:{org_id}:{api_key_id}` | In-flight counter for two-phase revoke drain | No |
| `chain:{org_id}:{chain_id}` | Chain state-machine hash | No | `CHAIN_IDLE = 300s` |
| `audit_hash:{organization_id}` | Last event's `content_hash` for chain fast-path | No | No TTL (cleanup-on-delete) |
| `session:{token}` | Session token → user lookup | user_id | 7d (`SESSION_MAX_AGE_SECS`) |

**No PII** is stored in any of the above keys. Token keys, user indexes,
and approval metadata carry only opaque IDs (UUIDs).

## 4. Hosting & placement

| Layer | Provider / location |
|---|---|
| **Cloud** | DigitalOcean LLC (US with EU regions). A single VPS hosts the whole deployment |
| **Postgres** | Self-hosted Docker container on the VPS, with a dedicated application role and the pgcrypto extension |
| **Redis** | Self-hosted Docker container on the same VPS, with AOF + RDB backup |
| **Object storage** | S3-compatible (`BACKUP_S3_BUCKET` env-gated). Compatible with DO Spaces via `S3_ENDPOINT` override. Audit export + backup upload |
| **Container orchestration** | Docker Compose on a single VPS. Blue-green deploys for budget/auth paths; rolling deploys for everything else |
| **CDN / edge** | None. nginx on the VPS terminates TLS and reverse-proxies. Direct origin exposure |
| **DNS** | nginx virtual hosts: `nullrun.io`, `www.nullrun.io`, `api.nullrun.io`. DNS provider not documented |

### Container hardening

Per the production container configuration:

- `read_only: true` root FS
- `cap_drop: [ALL]`
- `no-new-privileges: true`
- `tmpfs /tmp` (noexec / nosuid / nodev, 100M)

### TLS

- `ssl_protocols TLSv1.2 TLSv1.3;` (no SSLv3 / TLS 1.0 / 1.1)
- Mozilla "intermediate" cipher list
- HSTS preload candidate, `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- Certbot-managed Let's Encrypt at `/etc/letsencrypt/live/nullrun.io/`
- `[V]`

## 5. Access controls

### 5.1 RBAC

4-level hierarchy:

| Role | Level | Used for |
|---|---|---|
| Viewer | 0 | Read-only dashboard |
| Operator | 1 | Operator-tier mutations (kill / pause workflows, decide approvals). **Runtime-tier only** — does not exist in storage |
| Admin | 2 | Org management, member management |
| Owner | 3 | Org deletion, billing changes, ownership transfer |

**Storage-layer role** is parallel but not isomorphic:
`Viewer / Member / Admin / Owner`.

**Machine API keys** carry no user role. RBAC-protected mutations
require a user-bound key.

**Platform admin** additionally requires TOTP enabled + Owner role;
fail-CLOSED on TOTP-lookup error.

### 5.2 Auth methods

| Method | Wire |
|---|---|
| Session cookies (browser) | `__Host-nullrun_session` (prod) / `nullrun_session` (dev). The `__Host-` prefix requires Secure + Path=/ + no Domain. HttpOnly, SameSite=Lax, 7-day TTL. Fails CLOSED to prod (not dev) by default |
| API keys (machine) | `nr_live_*` prefix; HMAC-SHA256 over `timestamp + ":" + api_key + ":" + body_hash`. Key rotation is versioned and fanned out to every instance. Constant-time comparison |
| OAuth (identity) | GitHub + Google OAuth 2.0 redirect |
| SSO | SAML / OIDC single sign-on |

### 5.3 2FA

- **TOTP RFC 4226:** 6 digits, 30s period, 160-bit secret, 10 recovery
  codes on enable. Setup/verify/disable/recovery-codes endpoints under
  `/api/v1/auth/2fa/*`.
- **Platform admin endpoints** require TOTP-enabled user.
- **Recovery tokens** for OAuth users disabling 2FA: 24h TTL, held in
  Redis, single-use.
- `[V]`

### 5.4 API key scopes

- `SCOPE_ADMIN` is required for non-Owner admins on `/admin/*` paths.
- Workflow binding: API keys carry `workflow_id`; the body
  `workflow_id` MUST match the authenticated key's workflow, else
  `400 WORKFLOW_ID_BODY_MISMATCH`.
- Status: `active` / `rotating` / `revoked`.

### 5.5 Audit log access

- **Plan-gated:** `plan.features.audit_log` controls read access; Lite
  plan has `audit_log: false` (no customer access).
- **RLS:** a per-org SELECT policy on the audit log. Every raw
  database reader must set the current-organization context.
- **Plan tier retention:** `plan.history_days` controls
  customer-visible history retention; `-1` = unlimited.

### 5.6 Operator access to production

- SSH only via the allowlisted `vps` wrapper. Allowlisted
  subcommands: `redis-cli`, `psql`, `journalctl -u <unit>`.
- **Blocked:** `printenv`, `docker inspect`, raw `cat` of `.env.prod`,
  mutating docker subcommands.
- Production creds sourced from GH Secret `ENVPROD_FILE`, atomic render
  by CI.

## 6. Encryption

| Layer | Mechanism | Attestation |
|---|---|---|
| **In transit — server edge** | TLS 1.2 / 1.3, Mozilla intermediate ciphers, HSTS preload candidate | `[V]` |
| **In transit — WebSocket** | HMAC-SHA256 over canonical JSON, replay window 300 s | `[V]` |
| **At rest — Postgres (column)** | pgcrypto AES, hex-encoded. Applied to Slack OAuth bot tokens. Threat model: stolen DB dump + missing `APP_ENCRYPTION_KEY` = ciphertext | `[V]` |
| **At rest — Postgres (disk)** | **Not attested**; relies on DigitalOcean droplet disk encryption | `[N]` |
| **At rest — Redis** | **Not attested**; bind-mounted AOF/RDB volumes rely on host disk encryption | `[N]` |
| **At rest — S3 / object storage** | S3-compatible object storage, gated on `BACKUP_S3_BUCKET`. Bucket-side encryption (SSE-S3 / SSE-KMS) configuration is **not exposed** | `[D]` |
| **KMS / key management** | `APP_ENCRYPTION_KEY` env var drives pgcrypto AES. No AWS KMS / GCP KMS / HashiCorp Vault integration. Rotation requires a manual runbook (breaks 2FA and Slack) | `[D]` |
| **HMAC for request signing** | `NULLRUN_GATEWAY_SIGNING_KEY` (≥32 bytes, never auto-generated), used for HMAC-SHA256 of gate/execute/track bodies | `[V]` |
| **API keys at rest** | `key_hash` SHA-256 stored; `secret_key` plaintext stored (HMAC hot-path requirement). Key prefix / suffix surfaced for UI display | `[V]` |
| **Cookie security flags** | `__Host-` prefix, Secure, HttpOnly (session), SameSite=Lax, Path=/, 7-day Max-Age. CSRF cookie NOT HttpOnly (SPA reads it). Production = fail-CLOSED default | `[V]` |
| **Audit export signing** | Per-export HMAC-SHA256 sidecar via `NULLRUN_AUDIT_EXPORT_SECRET` (or per-org secret). Fail-CLOSED in prod (no dev fallback) | `[V]` |

## 7. Sub-processors

The canonical list is versioned and served from the public endpoint
`GET /api/v1/subprocessors` (ETag-cached).

| Sub-processor | Role | Country | Transfer mechanism | Opt-in |
|---|---|---|---|---|
| **DigitalOcean LLC** | Hosting (PG, Redis, app servers) | US (EU regions) | EU SCCs (Module 2/3) for US-region; EU residency available | No |
| **Brevo (Sendinblue GmbH)** | Transactional email | DE (Germany) | Adequacy decision (EU) | No |
| **Polar.sh (Polar Software Sweden AB)** | Payment, subscriptions, tax (merchant of record) | SE (Sweden) | Adequacy decision (EU) | No |
| **Slack Technologies, LLC** | Alert delivery (OAuth) | US | EU SCCs (Module 3) | Yes |
| **GitHub Inc.** | OAuth identity provider | US | EU SCCs (Module 3) | Yes |
| **Google LLC** | OAuth identity provider | US | EU SCCs (Module 3) | Yes |

**LLM providers:** NULLRUN does not proxy calls to OpenAI /
Anthropic / Google / Azure. The SDK talks to providers directly with its
own keys.

**Analytics / observability vendors:** Self-hosted stack — Prometheus,
Grafana, alertmanager, vector, and Loki. No Datadog / Sentry / Segment /
Mixpanel / Amplitude.

**Backup storage:** S3-compatible (`BACKUP_S3_BUCKET` env-gated); config
tar encrypted with GPG before upload.

## 8. Deletion

### 8.1 Organization deletion

**Soft-delete path**:

- The organization row is marked deleted, and a purge date is set 60
  days out.
- Audit rows **intentionally retained** during grace for SOC2 immutability.
- Owner can restore via `/restore` endpoint, which clears both.
- Handler returns `409 AUDIT_HISTORY_RETAINED` with `grace_period_days: 60`
  when audit history exists.
- Child records (API keys, policies, workflows, invites) are updated in
  the same transaction.

**Hard purge path:**

- Runs hourly after `audit_purge_after`.
- Scrubs the audit log, decision history, cost events, and billing
  events.
- Deletes the organization row.

**Audit immutability bypass:** within the same transaction the update and
delete triggers on the audit event table are disabled, the rows are
deleted, and the triggers are then re-armed with `ENABLE ALWAYS TRIGGER`
so they cannot be bypassed again by a session-level setting.

### 8.2 User account deletion

`DELETE /api/v1/auth/account`. Three cases:

| Case | Behaviour |
|---|---|
| Sole-owner sole-member org | Auto soft-deleted (no decision required) |
| Co-member org, decision = `delete_and_notify` | Soft-delete + fail-CLOSED revoke of all co-member sessions |
| Co-member org, decision = `transfer { to_user_id }` | Promote new owner, no delete |

Wire-additive: an `ownership_decisions` map keyed by user id.
Fail-CLOSED if Redis hiccups on session revoke (503). `[V]`

### 8.3 API key revocation — two-phase with in-flight drain

1. **Phase 1:** the key transitions to `rotating` and every instance is
   notified; a deny list short-circuits warm-cache hits.
2. **Phase 2:** a drain supervisor polls the
   `in_flight:{org_id}:{api_key_id}` counter until it reaches 0 or the
   timeout expires.
3. **Phase 3:** status → `revoked`. The counter does not return
   (preserved for audit / reconciliation).

TTL of the deny list = 2× the auth-cache TTL = 600 s.

### 8.4 GDPR / right-to-erasure

| Right | Implementation |
|---|---|
| **Art. 15 — right of access** | `POST /api/v1/auth/data-export`, a per-user export job. 7-day download TTL, 100k-record cap per section |
| **Art. 17 — right to erasure** | The tenant purge scrubs tenant-scoped data; triggered automatically 60 days after org soft-delete. No manual kickoff path is documented for self-serve |
| **Audit retention on erasure** | Audit rows are physically deleted when the org is purged (after the 60-day grace). Before the purge they are retained even on soft-delete (intentional — SOC 2) |
| **Drift guard** | An automated check prevents payloads from accumulating PII (e.g., email) that would later need GDPR erasure to scrub |

## 9. Data residency & sovereignty

- **Physical storage:** DigitalOcean droplets. Region selectable at
  signup: customers who pick EU get EU-resident Postgres / Redis.
- **Cross-region replication:** **Not attested**. Single-region
  deployment posture.
- **Cross-border transfers:**
  - US sub-processors (DO US regions, Slack, GitHub, Google) →
    **EU SCCs (Decision 2021/914) Module 2/3**.
  - EU sub-processors (Brevo DE, Polar SE, DO EU) → adequacy decision
    (no SCC needed).
- **In-product region enforcement:** customers who select EU residency
  at signup have data physically in EU. Wire transfers: EU SCCs for US
  endpoints; otherwise data never leaves EU. `[D]`
- **Customer-side region selection:** the DPA states that EU residency
  is available and is the default for customers who select the EU
  region; the signup-time selection mechanism is not exposed. `[D]`

## 10. Compliance posture

| Item | Status | Attestation |
|---|---|---|
| **DPA** | Available. `GET /api/v1/orgs/{org}/dpa` returns the accepted version + history; `POST /api/v1/orgs/{org}/dpa/accept` is idempotent on `(org_id, dpa_version)`. Acceptance is recorded as a `compliance.dpa.accepted` audit row. | `[V]` |
| **DPA text version** | Versioned. The accepted version is returned by the endpoint; the sub-processor list carries its own pinned version. | `[V]` |
| **Sub-processor endpoint** | `GET /api/v1/subprocessors` (public, ETag-cached) | `[V]` |
| **GDPR Art. 15** | Per-user export implemented | `[V]` |
| **GDPR Art. 17** | Right-to-erasure via the tenant purge (60-day grace) | `[V]` |
| **SOC 2** | The audit-log immutability guarantee is the SOC 2 control surface. **No SOC 2 Type II report is available.** | `[D]` |
| **ISO 27001** | **Not claimed** | `[N]` |
| **HIPAA** | **Not claimed** | `[N]` |
| **CCPA** | **Not claimed** | `[N]` |
| **Privacy policy URL** | Reachable from the `/dpa` and `/privacy` pages | `[N]` |
| **Audit export** | HMAC-signed JSONL / S3 download, produced by a background worker | `[V]` |

## 11. Breach & incident response

| Item | Status | Attestation |
|---|---|---|
| **Alerting surface** | Self-hosted **Prometheus alertmanager** + Slack (per-channel via OAuth). Alert rules cover track error rate >1% for 2m, P95 >200ms for 5m, P99 >500ms for 3m, out-of-order events, and similar. PagerDuty is not supported. | `[V]` |
| **Alert channels** | `Webhook` and `Slack`. Email, PagerDuty, and Discord channels are not supported. | `[V]` |
| **Runbooks** | 30+ topic-specific runbooks (track-error-rate, audit-drain-stuck, outbox-dlq, period-rollover-decision, envprod-leak, billing-drift, etc.) | `[V]` |
| **Status page** | **Not referenced** | `[N]` |
| **Breach-notification SLA** | **Not documented** | `[N]` |
| **On-call rotation** | **Not documented** | `[N]` |

## 12. Penetration testing

| Item | Status |
|---|---|
| **Internal pentest** | A comprehensive pentest profile plan exists, executed in phases against a local Docker stack |
| **Findings materialised in code** | `ENABLE ALWAYS TRIGGER` hardening closed an audit-event immutability bypass via `session_replication_role='replica'` |
| **External pentest report** | **Not available** |
| **Bug bounty program** | **Not advertised** |

## 13. Other load-bearing controls

- **HMAC required for all gate calls.** `NULLRUN_HMAC_REQUIRED=true`
  enforced in production. Missing / invalid → reject before enforcement.
- **Protocol header required.** `X-NULLRUN-PROTOCOL` on every gate
  request; `/health` returns min/max (min=2, max=4, current=4).
- **Fail-CLOSED on enforcement paths.** Budget path (Redis down → 402
  `REDIS_UNAVAILABLE`).
- **IDOR guards.** Body org mismatch, `workflow_id` body-vs-key
  mismatch, parent-execution cross-org rejection.
- **CSRF double-submit** for browser POSTs; `Authorization: Bearer`
  bypasses for API path. SHA-256-then-constant-time comparison.
- **PII redaction** for log lines.
- **Secret scanning pre-commit.** trufflehog (~700 provider sigs) +
  gitleaks (NullRun-specific key shapes). 500 KB max file size.

## Honest gaps

These items are either not documented or rely on third-party evidence.
They are the questions a vendor reviewer should follow up on:

### Not attested `[N]`

1. **SOC 2 / ISO 27001 / HIPAA / CCPA formal attestations.** No
   certificates or reports are available. The "SOC 2 immutability"
   wording refers to a self-imposed control, not third-party
   certification.
2. **External penetration test report.** Only an internal pentest plan
   and journal exist.
3. **Bug bounty program.** Not advertised.
4. **Status page.** No reference to `status.nullrun.io` or similar.
5. **Public breach-notification SLA / DPA SLA.** Not documented.
6. **Postgres tablespace / disk-level encryption at rest.** pgcrypto
   column-level encryption is used for Slack OAuth bot tokens;
   full-disk / tablespace encryption is not explicitly attested (relies
   on DigitalOcean droplet disk).
7. **Redis disk encryption.** AOF/RDB volumes are bind-mounted; no
   explicit encryption-at-rest on Redis noted.
8. **S3 / object-storage encryption settings.** S3-compatible object
   storage is implemented; bucket-side encryption configuration
   (SSE-S3 / SSE-KMS) is not exposed.
9. **Customer-side region selection mechanism.** The DPA wording ("EU
   residency available (default for customers who select the EU
   region)") references a signup-time choice; the wire path that
   records the customer's region preference is not exposed.
10. **DPA and privacy pages.** The public `/dpa` and `/privacy` pages
    were not part of this review.
11. **Cross-region replication / DR posture.** Single-region (one VPS)
    is the deployed topology. No documented failover.
12. **Privacy policy URL.** Not published on this site.

### Derived, not directly attested `[D]`

13. **Wire shapes for `/api/v1/proxy`.** The proxy request and response
    types are present and complete, but no live route registration was
    located.
14. **`api.nullrun.io` TLS minimum version on the SDK client side.**
    TLS 1.2/1.3 is enforced at the nginx edge; whether the SDK pins a
    minimum TLS version was not audited.
15. **KMS / key management.** `APP_ENCRYPTION_KEY` is an env var; no
    AWS KMS / GCP KMS / HashiCorp Vault integration. Key rotation
    requires a manual runbook.
16. **Operator access logs / session recording.** The production SSH
    access path is documented (`vps` wrapper); there is no evidence of
    operator-action audit logging on the database tier itself, beyond
    the audit rows the product writes.
17. **API key scopes beyond admin.** `SCOPE_ADMIN` is the only named
    scope. Granular scopes per workspace / operation were not
    enumerated.

## See also

- [Compliance overview](index.md)
- [Performance & limits](../operations/performance.md) — latency,
  failure-mode behaviour, timeouts
- [API keys](../concepts/api-keys.md) — HMAC, rotation, drain
- [Organization](../concepts/organization.md) — delete-org flow
- [Profile settings](../concepts/profile.md) — account delete flow
