---
title: Profile settings
maturity: stable
description: Your own account — name and email, password and two-factor authentication, active sessions, and how to delete the account.
---

# Profile settings

The **Profile settings** page is about you: the person signed in. It lives
under **Account → Profile** in the sidebar and is on every plan.

This is not the [Organization](organization.md) page. The organization page edits the workspace. This page edits your account.

## Your details

| Field | What it does |
|---|---|
| **Full name** | How you appear in the control center and in audit rows. |
| **Email** | The address you sign in with and where notifications reach you. |
| **Avatar** | Your initials on a colour tile, or the avatar from your identity provider when you signed in with one. |

The email address cannot be changed. The field is locked, and the server
refuses a change with `400`. Use a different email to register a new
account. A **Resend verification email** button appears while the
address is unverified, but only on an account that has a password.

## Password

The password section appears when your account has a password. Signing up with an identity provider instead gives you a **Set password** action.

Changing a password asks for the current one. Every other session ends, so
every other device has to sign in again. The browser you changed it in
stays signed in.

## Two-factor authentication

Two-factor authentication adds a one-time code from an authenticator app to every sign-in.

| State | What you can do |
|---|---|
| **Not configured** | **Enable** starts the enrolment. The server issues a secret and a QR code, and the first code from the authenticator confirms it. |
| **Enabled** | **Manage** opens the disable dialog. It asks for the current password. A **Generate new codes** link appears when three or fewer recovery codes are left. It also asks for the current password. |

Enabling it asks for no password. The server issues the secret to the
signed-in session, and the first code confirms the enrolment. Recovery
codes are shown once, at that moment. Only the number of codes left
stays visible.

If you lose the device, the recovery flow lets you disable two-factor authentication without it.

## Sessions

The session section holds one action:

| Action | Effect |
|---|---|
| **Log out** | Ends the session in this browser. You can sign back in at any time. |

The page does not list the sessions on your account and cannot end them
from another device.

## Deleting your account

At the bottom of the page, the **Danger zone** deletes your account. The endpoint is `DELETE /api/v1/auth/account`.

The request asks for:

| Field | When it is needed |
|---|---|
| **Confirmation** | Your full name, typed exactly. |
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
- Closes every organization you own that has no other member. An organization with other members follows the decision you made for it.

The account row goes first. If the session store is then unreachable, the
request fails with `503` and the account is already gone. Sign in again
rather than retrying the deletion.

The data of an organization you did not own is untouched. Closing an
organization on its own is a separate action on the
[Organization](organization.md) page.

## See also

- [Organization](organization.md) — the workspace, its members, and closing it
- [Team](team.md) — other people in the organization
- [Audit log](error-handling.md#audit-trail) — what the control center records
