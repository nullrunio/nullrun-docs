---
title: Team
maturity: stable
description: Members, invites, and the four-role matrix (owner / admin / operator / viewer) that governs what each teammate can do.
---

# Team

The **Team** page is the org-membership surface. It lists every
member and every pending invite, surfaces the per-role capability
matrix, and lets owners + admins invite or remove people. It lives
at `/control-center/team` in the sidebar under **Access** and is
gated by the `team` plan feature (Growth and above).

## Roles and what each can do

There are four roles, ranked from most to least permissive:

| Role | Capabilities |
|---|---|
| **Owner** | Everything an admin can do, plus transfer org ownership, delete the org, manage billing. There is always at least one owner; the last owner cannot be demoted. |
| **Admin** | Invite / remove members, change roles for non-owner members, edit all policies, manage API keys, configure notifications. Cannot delete the org or change billing. |
| **Operator** | Use the dashboard read/write — view workflows, executions, traces, audit log; approve / deny pending requests; create / edit policies and API keys. Cannot change team membership or billing. |
| **Viewer** | Read-only — view workflows, executions, audit log, MCP servers, but cannot mutate anything (including approve / deny). |

The full capability matrix is also rendered as a section inside
the page (so an admin can confirm what they're granting before
sending an invite).

## Members table

The members table is sortable by role (asc / desc) and shows:

- **Avatar** (initials in colour tile, or OAuth avatar for
  GitHub / Google users).
- **Name + email** (masked via `maskEmail` for non-self rows to
  prevent screen-shoulder disclosure).
- **Role** (select dropdown for owner / admin; non-owners show a
  select for the other three roles).
- **Joined at** (RFC-3339 timestamp; older rows predating the
  migration render `—`).
- **Remove** button (with confirmation dialog; the last owner
  cannot be removed).

Owners and the current user are pinned near the top of the list
regardless of sort order, so an admin never accidentally scrolls
past themselves.

## Invites

Above the members table is the **Invite** panel with an email
field + role selector. The dialog rejects:

- **Self-invites** — `You cannot invite yourself`.
- **Existing members** — `This person is already a member`.
- **Duplicate pending invites** — `Invite already sent to this
  email`.

Only owners and admins see the invite panel; operators and
viewers see a read-only members list.

After sending, the invite appears in a separate **Pending
invites** section below the members table. Each pending row
shows:

- **Email + role** + **Token** (copyable deep link).
- **Last send status** — `pending` / `sent` / `failed` (with
  SMTP error text on `failed`).
- **Last successful delivery** timestamp.
- **Resend** and **Revoke** buttons.

The invite link is `<APP_URL>/invite?token=<token>`; the deep
link is stable until the invite is revoked or accepted.

## Seat quota

The page header shows `N / <plan-cap> seats used`. The seat count
includes both active members and pending invites, so an admin
sees the quota cost of every outstanding invite in real time.

When the org hits the seat cap, the invite panel disables the
send button and surfaces an upgrade prompt — `Team seat limit
reached — N of N seats used` — that links to **Billing & Plan**
(`?tab=plan`).

## Plan gating

The Team page itself renders a `TierGate` upgrade prompt for
plans without the `team` feature; the sidebar link is also hidden.
Lite users cannot view the page, and the backend rejects every
member / invite mutation with `403 seat_feature_disabled`.

## Audit trail

Every invite send, resend, revoke, role change, and removal is
recorded in the audit log with the actor's `decided_by` UUID.
Admins can search the audit log by `action = team.*` to reconstruct
who did what to whom.

## Where to read next

- [Organization](organization.md) — for changing the org name,
  contact email, and DPA acceptance.
- [Billing & Plan](billing.md) — the Plan tab is where seat
  upgrades are purchased.
- [Audit log](error-handling.md#audit-trail) — every team
  mutation leaves a row.

## Deep dive

### Mechanism

Four-role matrix in `backend/src/auth/rbac.rs::Role`
(`Viewer < Operator < Admin < Owner`, an `Ord` enum so capability
checks can compare tiers). Storage-side roles live in
`db::OrganizationRole` — three names match (`Viewer / Admin /
Owner`) and one diverges: `Operator` is a runtime-action tier
between Admin and Viewer, while `Member` is the storage tier for
"regular user". The two enums are NOT isomorphic; the bridge
`Role::to_organization_role` returns `None` for `Operator` so
callers must explicitly decide whether to fall back to `Member`
or reject. Migrations 345 + 346 add `CHECK` constraints on the DB
column so the storage side stays the source of truth.

Owner authority is **bootstrap**: the `organizations.owner_user_id`
column grants it regardless of plan. Admin authority is gated on
`plan::contract::Capability::Rbac` — `team.rs::check_caller_is_admin_or_owner`
calls `resolve_plan_for_org_overlay_strict()` (ADR-057 trial-aware)
and returns 503 + `Retry-After: 5` on plan lookup failure
(fail-CLOSED per `CLAUDE.md §4`). The check honours DB ownership
first, then `members.role` — a `role="admin"` row on a plan
without `Capability::Rbac` is treated as no admin authority
(INV-4 / Sprint N+1 fix).

Seat quota lives on `plan.limits.seats` (migration 137) with a
defensive merge to `plan.features.seats` if `limits.seats` is
absent. ADR-057 overlays Scale's 50-seat cap for an active Lite
trial. `team.rs::invite_handler` reads
`db.get_org_trial_state` and substitutes `"scale"` before the cap
lookup. A `seats_used >= seats_limit` check returns
`429 seat_limit_exceeded`. Pending invites share the quota
(`list_organization_members` is the only counter — invites
incur a real cost).

Invites fan out via three side-effects: `db.create_organization_invite`
writes the row + token, `email::send_invite_email_async` dispatches
SMTP and writes `email_send_log` (migration 138), and
`alert::dispatch_member_invited_alert` fires the notification
bridge so the `member.invite` toggle in the dashboard surfaces.

### Guarantees

- Sole-owner invariant is structural — migrations 345/346 add the
  `CHECK` constraint and the `check_role_minimum` gate refuses to
  demote the last owner.
- Seat cap is hard fail-OPEN-with-rev-429 — operator sees the
  cap exceeded, no silent seat overage.
- Self-invite / duplicate pending invite / existing-member all
  reject with explicit 400s; each path is a guard, not an
  upsert.
- `remove_member_handler` immediately calls
  `SessionManager::revoke_user_org_sessions(member_uuid, org_uuid)`
  so the removed user cannot keep their cookie alive in that
  org.
- Plan resolution down is fail-CLOSED with `503` + `Retry-After`
  — never returns "false" (no silent fail-OPEN; same family as
  the gate-side budget cache).
- ADR-057 trial overlay applies only to *active* trials — a
  trial whose `expires_at <= now` falls through to the
  canonical Lite cap.

### Patterns

- Bootstrap owner authority: ownership column wins regardless of
  plan; plan downgrade does NOT reassign ownership (the DB
  invariant is preserved by the `update_plan`-time no-op on the
  owner column).
- Per-key `last_used_at` updates flow through the `X-API-Key`
  auth-cache hit path — no separate usage-tracking worker.
- Sole-owner sole-member gate on org delete
  (`organization.rs::delete_org_handler`) is mirrored by the
  team-page DELETE precondition, so the two surfaces can't
  disagree about who owns the org.
- Audit emit on every invite / resend / revoke / role change /
  removal — all under `action = team.*` for log search.

### Approaches

- Considered three roles (drop Operator). Chosen four —
  Operator is the "can approve but not mutate" tier that the
  approvals desk uses; collapsing loses that distinction.
- Considered per-org plan-gated owner authority. Chosen
  bootstrap authority — a downgrade should not strand the owner
  outside their own org.
- Considered pending invites not counting toward the seat cap.
  Rejected — admins need to see the real-time cost of outstanding
  invites, not be the one who finds out at accept time.

### Limitations

- `Operator` does not exist in `db::OrganizationRole` — every
  boundary that crosses enums MUST go through
  `Role::to_organization_role`, never `as_str()` against the
  sibling enum.
- Pending 2FA challenges live in memory by default; the Redis-backed
  `TwoFaStore` (GROWTH-4) keeps pending challenges alive across
  pod restarts but is opt-in via `with_redis`.
- Cross-org membership is not modelled — every row in
  `organization_members` belongs to exactly one org, so the
  invite token binds a recipient to one org only.
