---
title: Organization
maturity: stable
description: Org name / slug / contact email, DPA acceptance, and the irreversible delete-org flow at the bottom of the page.
---

# Organization

The **Organization** page is the workspace-level config surface —
the org's display name, slug, billing contact email, DPA
acceptance, and the irreversible delete flow. It lives at
`/control-center/organization` in the sidebar (no plan gate; every
plan can edit).

This page is **not** the billing surface — that lives at
[Billing & Plan](billing.md). This page covers org identity and
legal/compliance metadata only.

## Identity

The top section is the org identity form:

- **Name** — the display name shown in the dashboard header,
  email headers, and audit rows. Editable by owners; takes effect
  immediately on save.
- **Slug** — the URL-safe identifier; immutable post-creation.
  Used in deep links, invite URLs, and webhook URLs.
- **Contact email** — the address Polar and our support team
  contact for billing and security notifications. Owners can edit;
  the change triggers a confirmation re-auth (password or 2FA).

The Save button is disabled when the form is unchanged or when
the current user lacks the `owner` role. The success toast shows
the new name; the page does not navigate.

## DPA / Compliance

A dedicated section surfaces the org's Data Processing Agreement
acceptance status. The section reads:

- `accepted v2026-06-25 on 2026-08-15` (the **latest** acceptance),
  or
- `not yet accepted` (when the org has never accepted).

Below the latest line, a history of every prior acceptance —
`version · accepted_at · accepted_method`. Acceptance methods on
the wire are `in_product` (clicked through the dashboard) or
`signed_pdf` (an offline acceptance that ops imported).

When the latest version is unaccepted, the section renders an
inline **Accept DPA** button. Acceptance is idempotent on
`(org_id, dpa_version)` so a re-click is harmless — the backend
returns the existing row with `created: false`. The
`accepted_method` for the dashboard button is `in_product`.

DPA fetch + acceptance failures do not block the page render —
the section shows an inline retryable error and the rest of the
page stays interactive.

## Members (linked from here)

The page does not host the members table itself — the link in
the team section takes the operator to the **Team** page
(`/control-center/team`) under **Access**. Plan-gated to
Growth+.

## Delete organization (irreversible)

At the bottom of the page, the **Danger zone** section exposes
the irreversible delete flow. The button is **Delete
organization** and is only rendered when the current user has
the `owner` role AND is the only remaining owner; otherwise the
button is hidden and a one-line explainer tells the operator
which precondition is missing.

The confirmation dialog requires the operator to type the org
name verbatim into a confirm field — `Type "acme-ai" to confirm`.
Submitting fires a single `DELETE /api/v1/orgs/{org_id}` that
cascades:

- All workflows, executions, traces.
- All policies, approval rules, alerts, audit rows.
- All API keys (server-minted; the org loses access immediately).
- All team memberships + invites.

The dashboard then signs the operator out and redirects to
`nullrun.io`.

There is no undo. The 30-day audit-log retention still applies —
audit rows are tombstoned rather than destroyed, so a
post-delete forensic query through support is still possible
within the retention window. After 30 days, the audit rows are
purged.

## Audit trail

Every identity change (name, contact email) and every DPA
acceptance is recorded in the audit log with the actor's
`decided_by` UUID. The irreversible delete-org flow writes a
single audit row before cascade, marked `action = org.delete`,
which is retained for the full retention window regardless of
subsequent tombstones.

## Where to read next

- [Team](team.md) — invites, role matrix, seat quota.
- [Billing & Plan](billing.md) — for changing the plan or seat
  count.
- [Audit log](error-handling.md#audit-trail) — every identity
  change leaves a row.

## Deep dive

### Mechanism

Org identity is read by `proxy/http/organization.rs::org_handler`
in five steps: (1) load org via
`get_organization_including_soft_deleted` (so soft-deleted orgs
still surface during the grace period), (2) resolve
`effective_ctx = resolve_plan_for_org(db, org_uuid, now)` (the
ADR-057 trial-aware resolver that overlays Scale entitlements on
Lite trials), (3) count members, (4) count active workflows via
`count_active_workflows` (filters state + archived + deleted so
tombstoned rows don't inflate the count past the plan cap —
v3.47 fix), (5) fetch trial state separately rather than widening
`OrganizationRow` (one extra SELECT per page hit; the React
Query layer caches for 30s).

Update path (`update_org_handler`) requires at least one of
`name` or `contact_email`; an empty body returns 400 so callers
get a hard fail instead of a silent `updated_at` bump. Contact
email change triggers a confirmation re-auth (password / 2FA).

DPA acceptance is idempotent on `(org_id, dpa_version)` — a
re-click returns the existing row with `created: false`. Two
acceptance methods on the wire: `in_product` (clicked through
the dashboard) and `signed_pdf` (offline acceptance ops imported).
History is rendered as `version · accepted_at · accepted_method`.

Delete (`delete_org_handler`) chains five steps before returning
`204 NO_CONTENT`: owner check via `get_organization_including_soft_deleted`
(404 on mismatch — NOT 403, to avoid existence leak across
orgs), sole-owner sole-member gate via `count_active_members`
(`member_count > 1` → `409 ORG_HAS_MEMBERS` so the caller is
forced to `transfer_ownership` first), `db.delete_organization`,
invalidate + re-prime the policy cache for the org
(`refresh_org_keys_for_org` with a 500ms `tokio::time::timeout`
so the next `/gate` doesn't 402 on the cache-miss →
`max_budget_cents = 0` path — DEF-SDKT-006), and DEL the audit
hash chain head key (`audit_last_hash(org_id)`) so the chain
does not orphan.

### Guarantees

- Owner check is 404 not 403 — a non-owner who guesses an org UUID
  cannot distinguish "no such org" from "you're not the owner".
- Sole-owner sole-member gate is enforced by the handler — the
  soft-delete path can never silently nuke a co-member org.
- Post-delete audit rows are tombstoned, not destroyed — the
  30-day retention window still applies, so a forensic query
  through support is still answerable.
- Cache re-prime on delete is best-effort (timeout 500ms); a
  miss falls through to the periodic ticker (fail-CLOSED for the
  gate via DB fallback, not fail-OPEN).
- DPA acceptance is idempotent — re-submission returns the same
  row.

### Patterns

- Owner via `organizations.owner_user_id` (bootstrap authority)
  — plan downgrade does NOT reassign.
- Pre-delete cache invalidation pattern (`invalidate_org` +
  re-prime with timeout) is shared by `delete_api_key_handler`,
  `remove_member_handler`, `transfer_ownership_handler`, and
  `delete_org_handler` — same timeout, same fallback.
- DPA `version` is monotonic — acceptances for `v2026-06-25`
  before any later `vYYYY-MM-DD` show as history lines.
- Audit chain is PG-only (ADR-009 four-table separation) — the
  Redis head key is best-effort cleanup (CACHE-3 / GROWTH-7).

### Approaches

- Considered hard delete with cascade. Chosen soft-delete + 60-day
  grace + tombstone audit rows — soft-delete lets the owner still
  DELETE / RESTORE a soft-deleted org within the grace period
  via `get_organization_including_soft_deleted`.
- Considered revoking the caller's session on delete. Removed
  2026-09-01 after a user-confirmed dead-end: the
  `delete-account-modal` flow calls `DELETE /api/orgs/{id}` and
  then `DELETE /api/auth/account` in the same session. Revoking
  in step 1 401'd step 2. Other members lose access at the data
  layer via the soft-delete filter.
- Considered a hard `403 ORG_HAS_MEMBERS` on the member-count
  gate. Chosen `409 ORG_HAS_MEMBERS` with a remediation hint so
  the UI can render the right CTA (`Transfer ownership`).

### Limitations

- Sole-owner sole-member only — co-member orgs must transfer
  first via `transfer_ownership_handler`. There is no
  auto-cleanup path that bypasses transfer.
- Soft-delete grace period is 60 days; after that the org is hard
  purged (the audit rows survive to the retention-window tombstone).
- Redis head-key cleanup is best-effort — a stale head is
  overwritten by the next write (impossible post-delete) or by a
  `verify_chain` reconcile pass.
- The session is preserved on delete-org-side on purpose — the
  caller may want to do account deletion in the same modal flow.
