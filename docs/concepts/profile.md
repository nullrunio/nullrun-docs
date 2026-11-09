---
title: Profile settings
maturity: stable
description: Your own account — name and email, password and two-factor authentication, active sessions, and how to delete the account.
---

# Profile settings

The **Profile settings** page is about you: the person signed in. It lives under **Profile** in the sidebar and is on every plan.

This is not the [Organization](organization.md) page. The organization page edits the workspace. This page edits your account.

## Your details

| Field | What it does |
|---|---|
| **Display name** | How you appear in the control center and in audit rows. |
| **Email** | The address you sign in with and where notifications reach you. |
| **Avatar** | Your initials on a colour tile, or the avatar from your identity provider when you signed in with one. |

Changing the email asks for a confirmation — a password or a two-factor code — and sends a verification message to the new address. The address is not live until you click the link in it. A **Resend verification email** button appears while the address is unverified.

## Password

The password section appears when your account has a password. Signing up with an identity provider instead gives you a **Set password** action.

Changing a password asks for the current one. Every session ends, so every device has to sign in again.

## Two-factor authentication

Two-factor authentication adds a one-time code from an authenticator app to every sign-in.

| State | What you can do |
|---|---|
| **Not configured** | **Enable 2FA** shows a secret and a QR code. The first code confirms the enrolment. |
| **Enabled** | **Disable 2FA**, **Regenerate backup codes**, and **Regenerate secret**. Each asks for the current password and a fresh code. |

Enabling it asks for the current password before it issues a secret. Backup codes are shown once, at the point the first code confirms the enrolment. Only the number of codes left and the time of the last use stay visible.

If you lose the device, the recovery flow lets you disable two-factor authentication without it.

## Sessions

The session section shows:

- The last sign-in time and address.
- The number of active sessions.

Two actions:

| Action | Effect |
|---|---|
| **Sign out of all other devices** | Ends every session except the one you are using. |
| **Log out** | Ends the session in this browser. |

Signing out of the other devices is recorded in the audit log.

## Deleting your account

At the bottom of the page, the **Danger zone** deletes your account. The endpoint is `DELETE /api/v1/auth/account`.

The request asks for:

| Field | When it is needed |
|---|---|
| **Confirmation** | Your display name, typed exactly. Your email address is accepted as a fallback. |
| **Current password** | When your account has a password. |
| **Two-factor code** | When two-factor authentication is on. |
| **Ownership decision** | For every organization you own that has other members. |

An ownership decision has two shapes:

| Decision | What happens |
|---|---|
| Transfer | The organization moves to another member. |
| Delete and notify | The organization closes and its members are told. Their sessions end. |

Leaving a decision out is refused with `OWNERSHIP_DECISION_REQUIRED`, and the response lists the organizations with their members so you can decide in place.

What deletion does:

- Removes your account. You cannot sign in again.
- Ends every session you hold.
- Writes one audit row per organization you were a member of.

Organization data is untouched. Closing an organization is a separate action on the [Organization](organization.md) page.

If a session cannot be ended, the whole operation stops and nothing is deleted. A half-finished deletion would leave live sessions pointing at an account that no longer exists.

## See also

- [Organization](organization.md) — the workspace, its members, and closing it
- [Team](team.md) — other people in the organization
- [Audit log](error-handling.md#audit-trail) — every profile change leaves a row
