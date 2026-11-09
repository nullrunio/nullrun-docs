---
title: Data handling & vendor review
maturity: stable
description: What data NULLRUN transmits, stores, where it is hosted, who can access it, and how it is deleted — written for vendor security and compliance reviews.
---

# Data handling & vendor review

A consolidated answer to the standard vendor-risk questionnaire, for
an employee assessing NULLRUN as a vendor. Every value reflects the
deployed product. Rows marked **Not attested** are honest gaps: the
implementation does not document them.

This page is the detailed companion to the
[Compliance overview](index.md). That page gives the short version.

**Reading conventions.** `[V]` = verified · `[D]` = derived or inferred
· `[N]` = not attested.

## At a glance

| Question | Answer | Section |
|---|---|---|
| What does the SDK send? | Tool name, cost estimate, optional typed business impact, optional action digest, and the argument bag. | [Data transmitted](#1-data-transmitted) |
| What does the backend store in Postgres? | Organization, user, key, workflow, policy, approval, cost, and audit rows. The audit table is immutable. | [Data stored](#2-data-stored) |
| What does the backend store in Redis? | Budget counters, execution bindings, rate-limit buckets, session and chain state. The session entries hold the user and organization id. | [Data stored](#2-data-stored) |
| Where is it hosted? | DigitalOcean, with EU regions available. Self-hosted Postgres and Redis on one VPS. | [Hosting](#3-hosting) |
| Who can access production data? | Four role levels. Production shell access through an allowlisted wrapper. | [Access controls](#4-access-controls) |
| How is it encrypted? | TLS at the edge, column-level encryption for Slack OAuth tokens and TOTP secrets, HMAC-SHA256 for request signing and audit exports. | [Encryption](#5-encryption) |
| Which third parties see data? | DigitalOcean, Brevo (DE), Polar (SE), Slack, GitHub, Google. | [Sub-processors](#6-sub-processors) |
| How is data deleted? | Soft-delete with a 60-day grace, then a purge of tenant data. API key revocation is two-phase. | [Deletion](#7-deletion) |
| Where physically is data? | Region selectable at signup. Single-region deployment. | [Residency](#8-data-residency) |
| What is the compliance posture? | A data processing agreement is available at the org endpoint. No SOC 2, ISO 27001, or HIPAA attestation exists. | [Posture](#9-compliance-posture) |

## 1. Data transmitted

### 1.1 SDK to gateway

The gate request carries:

| Field | Source | Notes |
|---|---|---|
| `execution_id` | Gateway-minted | The gateway **mints a UUIDv7** and echoes it back. A client-supplied id is not honoured for ownership. |
| `trace_id`, `tool`, `mode`, `operation_id` | SDK-supplied | The request envelope. |
| `tool_arguments` | SDK-supplied | The call's argument bag. A `tool_params` field is accepted as an alternative name. A typed approval rule reads a named argument from it. |
| `business_impact` | SDK-supplied | Optional. Required only for typed approval rules. |
| `action_digest` | SDK-supplied | SHA-256 hex of the canonicalised payload. Verified again at execute time. |
| `workflow_id` | SDK-supplied | Must match the workflow bound to the authenticated key, or the request is refused with `WORKFLOW_ID_BODY_MISMATCH`. |

**Organization mismatch guard.** The organization in the body must
match the authenticated context. A mismatch is refused.

**No email address and no actor name** is sent by the SDK.

### 1.2 SDK to gateway, cost tracking

The cost-tracking request carries the event id, the workflow id, token
counts, the tool or model name, the provider, the model, trace and span
correlation ids, agent and organization ids, latency, retry flag, the
reserved amount, the provider-reported amount, a cost source label, and
free-form metadata.

The cost figure the client sends is **not trusted for enforcement**.
The gateway recomputes it.

### 1.3 Gateway to SDK

The gate response carries the decision, its source, an explanation, an
approval id when a human is required, the approval timeout, the
server-minted `execution_id`, and an echo of the action digest.

**PII in gate responses:** decision text, the explanation, and
approval ids. No email address, no organization name, no actor
identifier. `[V]`

### 1.4 Gateway to the LLM provider

- Provider types cover OpenAI, Anthropic, Google, and Azure.
- **NULLRUN does not proxy model calls.** The SDK talks to providers
  directly, using the customer's own API keys. `[D]`
- **Credential invariant:** NULLRUN holds no provider API key. The
  customer's key stays in the customer's process.

### 1.5 Control plane

- The WebSocket is signed with HMAC-SHA256 over canonical JSON, keyed
  by a per-API-key secret, with a 300-second replay window.
- The receiver verifies the decoded signed payload, not the raw wire
  bytes. `[V]`

### 1.6 Webhooks received

| Webhook | Verification |
|---|---|
| **Polar** (billing) | HMAC-SHA256 verified before any processing. Both Standard Webhooks headers and the `polar-signature` form are accepted. |
| **Slack events** | Signing-secret validation. Bot tokens are stored encrypted. |

### 1.7 Email

- **Sub-processor:** Brevo (Sendinblue GmbH, **DE**).
- **Email types:** invitation, invitation declined, two-factor
  recovery, password reset, verification, and data-export-ready
  notice.
- **PII redaction in logs:** an email address renders as a short
  SHA-256 prefix, never as plaintext. `[V]`

## 2. Data stored

### 2.1 Postgres

| Table | Stored | Mutable? | Encryption at rest | Retention |
|---|---|---|---|---|
| `audit_events` | Organization, actor, action, event type, decision, policy id, policy version, policy hash, matched rule, reason code, `execution_id`, `action_digest`, tool name and version, metadata, content hash, previous hash, timestamp | **Immutable** | Database level | Until the organization purge, after a 60-day grace |
| `execution_records` | One row per execution, joined on `execution_id` | Mutable | Database level | The plan's history window |
| `cost_events` | Cost in cents and millicents, token counts, provider-reported and authoritative cost, an integrity label, tool and model, correlation ids, agent and organization ids, receipt timestamp. Partitioned by month. | Mutable | Database level | The plan's history window |
| `approvals` | The decision, and who made it — a person, a system expiry, or an unknown source | Mutable: pending becomes approved, denied, expired, or revoked | Database level | Pending rows are collected by a sweep worker |
| `organizations` | Id, name, slug, contact email, plan, deletion timestamp, purge date | Mutable, soft delete | Database level | Hard-deleted by the retention worker after the grace |
| `users` | Id, email, display name, password hash (Argon2id), role, default organization, tombstone timestamp | Mutable | Database level | Until the organization cascade |
| `organization_api_keys` | Id, name, key prefix and suffix, the key hash (Argon2id), the SHA-256 lookup fingerprint, the HMAC signing secret, status, version, last use, expiry, scopes | Mutable | Database level | Until the organization cascade |
| `user_2fa` | The user id, the TOTP secret, the pending TOTP secret, and the hashed recovery codes | Mutable | Column-level encryption on the TOTP secrets | Until the user row is deleted |
| `policies` | Id, scope, policy type, enforcement mode, budget amount, overdraft cap | Mutable, soft delete | Database level | The plan's history window |
| `approval_rules` | The typed predicates that ask for a human, mirroring the policy quota | Mutable | Database level | The plan's history window |
| `workflows` | Metadata, state (normal, flagged, tripped, paused, killed), budget amount, archive and deletion timestamps | Mutable | Database level | Persistent |

**Sessions are not in Postgres.** Browser sessions live in Redis under a
7-day expiry, and hold the user id, the organization id, and the creation
time. The token itself is the key. A revocation writes a tombstone.

### 2.2 Immutability of the audit table

Four independent controls protect the audit table:

1. Row-level triggers refuse an update and a delete.
2. A schema-level event trigger refuses schema changes to the audit
   and audit-export tables.
3. Delete and truncate are revoked from the application role on the
   audit-export tables.
4. The triggers are armed so that a session-level replication-role
   change cannot disable them.

### 2.3 Column-level encryption

Column-level encryption uses pgcrypto AES. It is applied to the Slack
OAuth bot tokens, the TOTP secrets, and the MCP discovery bearer
tokens. The threat model: a stolen disk image or a read-only dump
yields ciphertext, and the plaintext needs both the database and the
encryption key.

### 2.4 Redis

Redis holds short-lived operational state. Grouped by purpose:

| Purpose | Contents | PII |
|---|---|---|
| Budget | The period cost counter, the reserved amount per execution | No |
| Execution binding | The organization and API key an `execution_id` belongs to | No |
| Rate limiting | Per-organization and per-key counters | No |
| Session and token | Session lookups and revocation tombstones, two-factor challenge and recovery tokens | User and organization id only |
| Chain state | The chain state machine for a chain of workflows | No |
| Audit chain fast path | The last event's content hash per organization | No |
| Circuit state | The workflow circuit-breaker state | No |

The keys hold opaque identifiers. The only personal data is the user
and organization id in the session entry.

## 3. Hosting

| Layer | Provider or location |
|---|---|
| **Cloud** | DigitalOcean LLC, US with EU regions. One VPS hosts the whole deployment. |
| **Postgres** | Self-hosted container on the VPS, with a dedicated application role and the pgcrypto extension. |
| **Redis** | Self-hosted container on the same VPS, with AOF and RDB backups. |
| **Object storage** | S3-compatible, for audit exports and backups. Compatible with DigitalOcean Spaces. |
| **Orchestration** | Docker Compose on one VPS. Blue-green deploys on the budget, billing, and gate paths; rolling deploys elsewhere. |
| **Edge** | No CDN. nginx on the VPS terminates TLS and reverse-proxies. The origin is directly reachable. |
| **DNS** | nginx virtual hosts for the marketing site and the API host. |

### Container hardening

- Read-only root filesystem.
- All Linux capabilities dropped.
- No privilege escalation.
- A tmpfs for temporary files, mounted noexec, nosuid, and nodev.

### TLS

- TLS 1.2 and 1.3 only.
- A Mozilla "intermediate" cipher list.
- HSTS with a one-year max age and subdomain inclusion.
- Certificates managed by Certbot. `[V]`

## 4. Access controls

### 4.1 Roles

| Role | Level | Used for |
|---|---|---|
| Viewer | 0 | Read-only access. |
| Operator | 1 | Operator-tier mutations: kill and pause workflows, decide approvals. This level exists only at runtime. |
| Admin | 2 | Organization and member management. |
| Owner | 3 | Organization deletion, billing changes, ownership transfer. |

The storage layer has a parallel hierarchy: viewer, member, admin,
owner.

**Machine API keys carry no user role.** A mutation that the role
model protects needs a user-bound key.

**Platform admin** additionally needs two-factor enabled and the owner
role. A lookup failure refuses the request.

### 4.2 Authentication

| Method | Wire |
|---|---|
| Session cookie (browser) | A host-prefixed cookie in production, HttpOnly, SameSite=Lax, 7-day lifetime. It fails closed to production rather than to development. |
| API key (machine) | A prefixed key; the request body is signed with HMAC-SHA256 over the timestamp, the key, and a hash of the body. Rotation is versioned and fans out to every instance. The comparison is constant-time. |
| OAuth (identity) | GitHub and Google. |
| SSO | SAML and OIDC single sign-on. |

### 4.3 Two-factor

- TOTP with six digits, a 30-second period, and ten recovery codes on
  enable.
- Platform-admin endpoints need a two-factor-enabled user.
- Recovery tokens for OAuth users disabling two-factor are
  single-use, hold a user id, and expire after 24 hours. `[V]`

### 4.4 API key scopes

- An admin scope is required for non-owner admins on admin paths.
- A key carries its workflow id. A body `workflow_id` that does not
  match the key is refused with `WORKFLOW_ID_BODY_MISMATCH`.
- Status: active, rotating, or revoked.

### 4.5 Audit log access

- **Plan-gated.** A plan feature flag controls read access. Plans
  without the flag give the customer no access.
- **Database policy.** A per-organization row policy exists on the
  audit table, and a raw reader must set the current-organization
  context. The deployed application role is a superuser with row-level
  security bypassed, so the policy does not bind there. Tenant scoping
  in production comes from the queries, not from the policy.
- **Retention.** The plan's history window controls customer-visible
  history. A value of -1 means unlimited.

### 4.6 Operator access to production

- Shell access goes through an allowlisted wrapper that permits a
  small set of read-only commands.
- Blocked: environment dumps, container inspection, reading the
  production environment file, and every mutating container command.
- Production credentials come from a CI secret and are rendered
  atomically.

## 5. Encryption

| Layer | Mechanism | Attestation |
|---|---|---|
| **In transit, server edge** | TLS 1.2 and 1.3, Mozilla intermediate ciphers, HSTS | `[V]` |
| **In transit, WebSocket** | HMAC-SHA256 over canonical JSON, 300-second replay window | `[V]` |
| **At rest, Postgres columns** | pgcrypto AES, hex-encoded, on the Slack OAuth bot tokens, the TOTP secrets, and the MCP discovery bearer tokens | `[V]` |
| **At rest, Postgres disk** | **Not attested**; relies on the provider's disk encryption | `[N]` |
| **At rest, Redis** | **Not attested**; the backup volumes rely on host disk encryption | `[N]` |
| **At rest, object storage** | S3-compatible storage. Bucket-side encryption settings are **not exposed** | `[D]` |
| **Key management** | One environment-held key drives the column encryption. No managed key service is integrated. Rotation needs a manual runbook, and it breaks two-factor and Slack until every copy is replaced | `[D]` |
| **Request signing** | HMAC-SHA256 over gate, execute, and track bodies. The signing key is at least 32 bytes and is never generated automatically | `[V]` |
| **API keys at rest** | The key itself is stored as an Argon2id hash. A SHA-256 fingerprint of the key is stored beside it, so the row can be found without a full hash verification. The signing secret is stored in plaintext because the hot path needs it. A prefix and suffix are kept for display | `[V]` |
| **Cookies** | Host prefix, Secure, HttpOnly for the session, SameSite=Lax, Path=/, 7-day lifetime. The CSRF cookie is readable by the single-page app by design | `[V]` |
| **Audit exports** | An HMAC-SHA256 sidecar signature, keyed by one deployment-wide secret held in the environment. The secret is required in production: with it unset and no explicit development, test, or staging environment set, the service refuses to start. A fixed development value is used only in those explicit non-production environments | `[V]` |

## 6. Sub-processors

The canonical list is served from a public endpoint and cached with an
entity tag.

| Sub-processor | Role | Country | Transfer mechanism | Opt-in |
|---|---|---|---|---|
| **DigitalOcean LLC** | Hosting: Postgres, Redis, application servers | US, with EU regions | EU standard contractual clauses for the US region | No |
| **Brevo (Sendinblue GmbH)** | Transactional email | DE | EU adequacy decision | No |
| **Polar.sh (Polar Software Sweden AB)** | Payment, subscription, tax, merchant of record | SE | EU adequacy decision | No |
| **Slack Technologies, LLC** | Alert delivery and OAuth | US | EU standard contractual clauses | Yes |
| **GitHub Inc.** | OAuth identity provider | US | EU standard contractual clauses | Yes |
| **Google LLC** | OAuth identity provider | US | EU standard contractual clauses | Yes |

**Model providers.** NULLRUN does not proxy calls to OpenAI,
Anthropic, Google, or Azure. The SDK talks to providers directly with
the customer's own keys.

**Analytics and observability.** Self-hosted: Prometheus, Grafana,
Alertmanager, Vector, and Loki. No third-party analytics vendor.

**Backup storage.** S3-compatible, with the configuration archive
encrypted before upload.

## 7. Deletion

### 7.1 Organization deletion

**Soft-delete.** The organization row is marked deleted and a purge
date is set 60 days out. Audit rows stay for the grace period because
the audit chain must stay intact. An owner can restore the
organization, which clears both markers. A delete request that would
leave audit history behind is refused with a `409` that names the
grace period and its length. Child records — keys, policies,
workflows, invitations — are updated in the same transaction.

**Hard purge.** The purge runs after the purge date. It scrubs the
audit log, the decision history, the cost events, and the billing
events, then deletes the organization row. The update and delete
triggers on the audit table are disabled inside that transaction and
re-armed afterwards, so they cannot be bypassed by a session-level
setting.

### 7.2 User account deletion

Three cases:

| Case | Behaviour |
|---|---|
| The only owner of the only member's organization | The organization is soft-deleted. No decision is required. |
| Co-member organization, the user chooses delete and notify | Soft delete, and every co-member session is revoked. A revocation failure refuses the request. |
| Co-member organization, the user chooses transfer | A new owner is promoted and nothing is deleted. |

The request carries an ownership-decisions map keyed by user id. A
session-revocation failure refuses the request. `[V]`

### 7.3 API key revocation

Three phases:

1. The key moves to rotating, every instance is notified, and a deny
   list short-circuits warm-cache hits.
2. A drain supervisor waits for the in-flight counter to reach zero,
   or for the timeout to expire.
3. The key becomes revoked. The counter is preserved for audit and
   reconciliation.

The deny list lives for twice the authentication cache lifetime.

### 7.4 GDPR

| Right | Implementation |
|---|---|
| **Access** | A per-user export job. The download expires after 7 days, and each section is capped at 100 000 records. The session section reads a Postgres table that the migrations do not create, so it comes back empty and the job logs it and continues. |
| **Erasure** | The tenant purge scrubs tenant-scoped data, and runs automatically 60 days after the soft delete. There is no self-serve kickoff path. |
| **Audit retention on erasure** | Audit rows are physically deleted when the organization is purged. They are retained through the grace period on purpose. |
| **Drift guard** | An automated check keeps personal data from accumulating in payloads where it would later need to be scrubbed. |

## 8. Data residency

- **Physical storage:** DigitalOcean. The region is selectable at
  signup, and a customer who picks EU gets EU-resident Postgres and
  Redis.
- **Cross-region replication:** **Not attested**. The deployment is
  single-region.
- **Cross-border transfers:**
  - US sub-processors — DigitalOcean US, Slack, GitHub, Google — use
    EU standard contractual clauses, modules 2 and 3.
  - EU sub-processors — Brevo in DE, Polar in SE, DigitalOcean EU —
    rely on the EU adequacy decision.
- **Region enforcement:** the region chosen at signup decides where the
  data physically sits. The signup mechanism is not exposed on the
  wire. `[D]`

## 9. Compliance posture

| Item | Status | Attestation |
|---|---|---|
| **Data processing agreement** | Available. The org endpoint returns the accepted version and its history. Acceptance is idempotent per version and is recorded as an audit row. | `[V]` |
| **Sub-processor list** | Served from a public endpoint, cached with an entity tag. | `[V]` |
| **GDPR access** | Per-user export implemented. | `[V]` |
| **GDPR erasure** | Right to erasure through the tenant purge, after a 60-day grace. | `[V]` |
| **SOC 2** | The audit-table immutability guarantee is the control surface. **No SOC 2 Type II report is available.** | `[D]` |
| **ISO 27001** | **Not claimed** | `[N]` |
| **HIPAA** | **Not claimed** | `[N]` |
| **CCPA** | **Not claimed** | `[N]` |
| **Audit export** | HMAC-signed JSONL or an object-storage download, produced by a background worker. | `[V]` |

## 10. Breach and incident response

| Item | Status | Attestation |
|---|---|---|
| **Alerting surface** | A self-hosted Prometheus Alertmanager plus Slack, with per-channel OAuth. Rules cover the cost-tracking error rate, latency percentiles, out-of-order events, and similar. PagerDuty is not supported. | `[V]` |
| **Alert channels** | Webhook and Slack. Email, PagerDuty, and Discord are not supported. | `[V]` |
| **Runbooks** | Topic-specific runbooks exist for the cost-tracking error rate, a stuck audit drain, a stuck outbox, a period rollover, a credential leak, and billing drift. | `[V]` |
| **Status page** | **Not referenced** | `[N]` |
| **Breach-notification SLA** | **Not documented** | `[N]` |
| **On-call rotation** | **Not documented** | `[N]` |

## 11. Penetration testing

| Item | Status |
|---|---|
| **Internal pentest** | A phased pentest profile exists, executed against a local Docker stack. |
| **Findings fixed in code** | Trigger hardening closed an audit-table immutability bypass that a session-level replication-role change could have opened. |
| **External pentest report** | **Not available** |
| **Bug bounty program** | **Not advertised** |

## 12. Other load-bearing controls

- **Signed gate calls.** Signature verification is mandatory in
  production. A missing or invalid signature is refused before
  enforcement runs.
- **Protocol header required.** Every gate request carries a protocol
  version header. The service publishes the minimum and maximum it
  accepts.
- **Fail-closed on enforcement paths.** When the budget store is
  unreachable the gate answers `402` with
  `BUDGET_REDIS_UNAVAILABLE`. It never answers "allow" without a
  budget answer.
- **Cross-tenant guards.** Body organization mismatch, workflow-id
  mismatch between the body and the key, and a parent execution from
  another organization are each refused.
- **CSRF double-submit** on browser POSTs, with a bearer-token
  exemption for API paths. The comparison hashes first and compares in
  constant time.
- **PII redaction** in log lines.
- **Secret scanning before commit.** Two scanners, one general and one
  for NULLRUN key shapes, plus a file-size limit.

## Honest gaps

These are the questions a vendor reviewer should follow up on.

### Not attested `[N]`

1. **Formal attestations.** No SOC 2, ISO 27001, HIPAA, or CCPA
   certificate or report exists. The immutability wording describes a
   self-imposed control, not a third-party certification.
2. **External penetration test report.** Only an internal plan and
   journal exist.
3. **Bug bounty program.** Not advertised.
4. **Status page.** No public status host is referenced.
5. **Breach-notification SLA.** Not documented.
6. **Disk-level encryption at rest.** Column-level encryption covers
   the Slack OAuth bot tokens, the TOTP secrets, and the MCP discovery
   bearer tokens. Full-disk or tablespace encryption relies on the
   provider's disk encryption.
7. **Redis disk encryption.** The backup volumes are bind-mounted
   with no documented encryption at rest.
8. **Object-storage encryption settings.** Bucket-side encryption
   configuration is not exposed.
9. **Customer-side region selection.** The agreement refers to a
   signup-time choice, and the wire path that records it is not
   exposed.
10. **Cross-region replication and disaster recovery.** The deployed
    topology is one region on one VPS. No failover is documented.
11. **Privacy policy page.** Not published on the site.

### Derived, not directly attested `[D]`

12. **Managed key service.** The encryption key is an environment
    value with no managed key service behind it, and rotation needs a
    manual runbook.
13. **Operator action logging.** The production shell path is
    allowlisted, and the product writes its own audit rows. There is
    no separate record of operator actions at the database tier.
14. **Granular API key scopes.** An admin scope is the only named
    scope. Per-workspace or per-operation scopes are not enumerated.
15. **Client-side TLS minimum.** TLS 1.2 and 1.3 are enforced at the
    nginx edge. Whether the SDK pins a minimum version was not
    audited.

## See also

- [Compliance overview](index.md)
- [Performance & limits](../operations/performance.md) — timeouts and
  the fail-closed posture
- [API keys](../concepts/api-keys.md) — signing, rotation, revocation
- [Organization](../concepts/organization.md) — the delete-organization
  flow
- [Profile settings](../concepts/profile.md) — the delete-account flow
