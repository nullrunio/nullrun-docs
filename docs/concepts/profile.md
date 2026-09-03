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

## Display preferences (retired)

The currency toggle was retired on 2026-08-11 (Audit P3-6
closure). Operators read "cost shown in EUR" as "I will be billed
in EUR", which the wire contract forbids — backend billing is
always USD-cents, and the section name + the per-card `USD`
suffix already communicate that. The component is retained for
any future surface that genuinely needs display conversion.

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
