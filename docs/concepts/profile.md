---
title: Profile settings
maturity: stable
description: Personal info, two-factor auth, sessions, and the delete-account flow — the per-user surface, distinct from the per-org Organization page.
---

# Profile settings

The **Profile settings** page is the per-user surface: personal
info, two-factor auth, password, sessions, and the
delete-account flow. It lives at `/control-center/profile` in the
sidebar (no plan gate).

This page is **not** the org-level **Organization** page — that
one edits org identity, slug, billing email, and DPA acceptance.
Profile is the *person* who is currently signed in.

## Profile hero

The hero card shows:

- **Avatar** — initials on a colour tile (chosen server-side via
  `avatar_color`), OR the OAuth avatar (populated for GitHub /
  Google users, null for email-registered users). The OAuth
  image takes precedence over the initials fallback when both
  exist.
- **Display name + email** + **Member since** timestamp.

## Personal info

A two-column form with:

- **Display name** — editable; saves on submit.
- **Email** — editable, but the change triggers a confirmation
  re-auth (password or 2FA) and a verification email to the new
  address. Until the operator clicks the verification link, the
  email chip reads `Verification pending`.
- **Resend verification email** — visible when the email is
  unverified. Disabled for 60 seconds after each click.

A **Saved** indicator next to the Save button acknowledges the
last write without taking up screen space.

## Security

A two-column security section covers:

- **Password** — visible when the user has a password (email-
  registered users). OAuth-only users (no `has_password` flag)
  see a one-line explainer + a **Set password** button that
  links to the password-set flow.

  The password change form requires the **current** password and
  validates the **new** password server-side. The dialog does not
  unmount on success — the user can change another field without
  re-entering the password.

- **Two-factor auth (TOTP)** — three states:
  - **Not configured** — `Enable 2FA` opens a modal that
    generates a TOTP secret, renders a QR code, and asks for the
    first 6-digit code to confirm. The current password is
    required (`requireCurrentPassword`) before the secret is
    shown.
  - **Enabled** — `Disable 2FA` and `Regenerate backup codes`
    (and `Regenerate secret`, depending on the build). Both
    require the current password and a fresh TOTP code.
  - **Pending recovery** — for users who lost their device;
    the `Regenerate` flow can also be used to rotate secrets.

  The 2FA status object (`{ enabled: boolean, backup_codes_remaining: number, last_used_at: string | null }`) drives the chip
  in the section header.

## Sessions

The **Session section** is a read-only card showing the
information security needs to know:

- **Last login** timestamp and IP.
- **Active session count** (the current browser + every other
  logged-in device the user has).
- **Sign out of all other devices** — single click, immediately
  invalidates every other session but keeps the current browser
  signed in. The action is logged in the audit log under
  `action = session.terminate_all`.
- **Log out** — single click, signs out the current browser only.

## Display preferences

The Display preferences section is reserved for per-user view
options. Backend billing is always USD-cents; every cost surface
carries a `USD` suffix to make that explicit.

## Danger zone

The **Delete account** button at the bottom of the page opens a
modal that:

- Requires typing the user's display name verbatim
  (`Type "Anatolii" to confirm`).
- Requires entering the current TOTP code **if 2FA is enabled**
  (otherwise just the password).
- Calls `DELETE /api/v1/me`, which tombstones the user, removes
  every session, and invalidates every API key the user
  personally minted. Org-level data (workflows, policies, audit
  rows) is untouched — that is the **Organization → Delete
  organization** flow, not this one.
- Signs the operator out and redirects to `nullrun.io`.

There is no undo. Audit rows authored by the deleted user
remain in the org's audit log (`decided_by` UUID preserved) so a
post-delete forensic query still works within the retention
window.

## Where to read next

- [Organization](organization.md) — the org-level identity page
  (different from this per-user page).
- [Audit log](error-handling.md#audit-trail) — every profile
  change (password / 2FA / email / sessions) leaves a row.

## Deep dive

!!! info "Deep dive"

    Per-user surface distinct from per-org Organization. Reads
    actor from session cookie `__Host-nullrun_session` (prod) /
    `nullrun_session` (dev) or `Authorization: Bearer
    <session_token>`. Cookie name resolution is
    `auth/cookies.rs::CookieEnv::current()` — fail-CLOSED on
    missing env (defaults to `Prod`, the `__Host-` prefix +
    `Secure` flag); the dev override requires
    `NULLRUN_DEV_MODE=true` AND `NODE_ENV != "production"`. The
    `OnceLock<CookieEnv>` is cached at first call so a missing
    or late-loaded `.env.prod` cannot flip a prod pod to Dev
    (a regression found 2026-07-15).

    2FA setup (`user_security.rs`) generates a 20-byte TOTP
    secret (RFC 4226 §4 R1), renders a base32-encoded
    `otpauth://` URI plus a QR SVG, and waits for the first
    6-digit code to confirm before promoting from pending to
    active. Setup requires current password
    (`requireCurrentPassword`). Recovery codes are 10 × 80-bit
    random strings, shown ONCE at promotion, then stored as
    `Argon2(password_hash, recovery_code)` pairs on the user
    row. Pending 2FA challenges (login → 2FA → verify) live in
    Redis (`PENDING_2FA` TTL 300s) since GROWTH-4 — the
    `TwoFaStore::with_redis` variant persists them so a user
    who hits pod B right after the challenge was issued by pod
    A still sees a valid token. Pre-GROWTH-4 in-memory storage
    meant the user would see `Invalid 2FA token` until they
    re-issued.

    Account deletion is `DELETE /api/v1/auth/account` (NOT
    `/api/v1/me`) — wired in `proxy/http/routes.rs`. Body shape
    (`DeleteAccountRequest`, ADR-048): typed `confirmation`
    (exact name match), optional `current_password` (iff
    `has_password`), optional `totp_code` (iff 2FA enabled), and
    `ownership_decisions: HashMap<OrgUuid, OwnershipDecision>`
    where the enum is `#[serde(tag = "action", rename_all =
    "snake_case")]` with `Transfer { to_user_id }` or
    `DeleteAndNotify`. Missing decisions for co-member owned
    orgs return `400 OWNERSHIP_DECISION_REQUIRED` with the full
    member roster. Session termination:
    `SessionManager::revoke_all_user_sessions` clears every
    `session:sess_*` whose data `user_id` matches, then follows
    with the per-token `session_org:{token}:*` SCAN (B1 fix —
    without this, the org-consistency cache would survive
    revoke for up to 60s and let a revoked token re-enter).

    Tombstoned user re-login returns `USER_NOT_FOUND` (ADR-041,
    `isTombstonedAuthResponse` in
    `frontend/lib/post-auth-redirect.ts`) — five BFF entry-points
    honour it (login, login-2fa, register, github callback,
    google callback). The `DeleteAndNotify` arm is fail-CLOSED
    on Redis hiccup (ADR-048 §5): if ANY co-member's
    session-revoke returns an error, the handler aborts with
    `503 SERVICE_UNAVAILABLE` and the org is NOT soft-deleted —
    the user's account is also not deleted. Two reasons: audit
    retention (no dangling session keys past TTL) and
    notification integrity (no unread "owner deleted the org"
    email + still-usable session). The `Transfer` arm does NOT
    revoke the new owner's session (they are now the owner);
    `DeleteAndNotify` does NOT revoke the departing owner's
    session (they're leaving anyway). TOTP secret is encrypted
    at rest with `APP_ENCRYPTION_KEY`; decryption failure
    surfaces as `APP_ENCRYPTION_KEY drift` (audit trail marker).
    `revoke_all_user_sessions` clears BOTH the session key and
    the derived `session_org:{token}:*` cache — single SCAN per
    org, no stale-window bypass. FKs on user-owned rows go to
    NULL on user delete (migration 203:
    `organization_api_keys.created_by_user_id`; migration 204:
    `admin_audit_log.actor_user_id`) so account delete is not
    blocked by 23503. Audit rows authored by a deleted user stay
    in the org's audit log (`decided_by` UUID preserved) —
    forensic story is intact for the retention window.

    Per-action audit emission via
    `audit::persistence::record_security_audit_event` — every
    profile mutation (password / 2FA / email / sessions) goes
    through the typed wrapper so the policy-gated persistence
    classes (`AuditPersistenceClass::SecurityEvidence`) are
    uniformly enforced. Ownership cascade is single-pass per
    owned org: iterate, decide, execute, with no remediation
    round-trips (ADR-048 §4 — the earlier "POST then DELETE"
    anti-pattern was rejected for race window + partial-failure
    UX). `revoke_user_org_sessions(member_uuid, org_uuid)`
    (single member, single org) is used by
    `remove_member_handler` so member removal does not require
    `revoke_all_user_sessions`.

    Considered per-org POST/DELETE round-trip per conflict —
    rejected (ADR-048 §4) for race window between two parallel
    round-trips, partial-failure UX, and PUT-on-DELETE semantic
    smell. Considered mandatory transfer (drop
    `delete_and_notify`) — rejected: spec'd case-2 ("if no one
    is selected for transfer → org deleted, all members kicked
    out") and the last-active-owner scenario where closing is
    the only viable action. Considered drop co-member support
    — rejected: forces the user out of the deletion flow to do
    prerequisite work in another part of the app. Considered
    in-memory 2FA store and reverted to Redis-backed after
    GROWTH-4 surfaced the cross-pod challenge-loss bug.

    Wire change is a hard cutover — no protocol bump. The
    `X-NULLRUN-PROTOCOL` header is bound to `/check` /
    `/execute` / `/track` (ADR-013), not user-management
    endpoints. Older clients without `ownership_decisions` fall
    into the 400 path; the modal retries with decisions
    automatically. The surface is browser-only — no third-party
    SDK consumes `DeleteAccountRequest`, so the body shape
    change is safe. `APP_ENCRYPTION_KEY` rotation requires a
    runbook — it breaks 2FA + Slack (the encrypted TOTP secrets
    and webhook signing keys are pinned to the old key).
    `revoke_all_user_sessions` SCAN cost is bounded by
    `session:sess_*` cardinality on Redis; for very large pods,
    the count of revoked tokens is bounded by the user's own
    session history.
