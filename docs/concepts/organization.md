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
Starter+.

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
