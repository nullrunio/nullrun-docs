---
title: Organization
maturity: stable
description: The workspace that owns your workflows, policies, keys, people, and spend — its identity, its DPA acceptance, and how to close it.
---

# Organization

An **organization** is the workspace that holds everything: workflows, policies, approval rules, API keys, members, and spend. Every plan has one.

The **Organization** page covers the organization's identity and its legal metadata. The plan and the seats live under [Billing & Plan](billing.md), and the people live under [Team](team.md).

## Identity

| Field | What it does |
|---|---|
| **Name** | The display name in the control center, in email headers, and in audit rows. |
| **Slug** | The URL-safe identifier. It is fixed for the life of the organization. |
| **Contact email** | The address billing and security messages go to. |

An owner edits the identity on every plan. An admin edits it on Growth and
above. On Lite and Starter an admin is refused, because the role check
needs the plan's RBAC feature.

The change lands in one request. The server takes the new name and the new
contact email and applies them.

## Data Processing Addendum

The **Compliance** section shows whether the organization has accepted the current Data Processing Addendum. It names the current version and links to it with **Read v{version}**.

| State | What the section shows |
|---|---|
| The current version is accepted | A green **Accepted** badge with the acceptance date. |
| Nothing is accepted | A button **Accept v{version}**. |
| An older version is accepted | A notice that a new version is available, and a button **Re-accept v{version}**. |

Accepting the same version twice is harmless. The record keeps the date of the first acceptance, and its method label shows the latest acceptance.

### Acceptance history

**Acceptance history (N)** lists one row per accepted version, newest first. Each row carries the version, the date, and how it was accepted, written as `via {method}`.

| Method | Meaning |
|---|---|
| `in_product` | Accepted by clicking through the control center. |
| `signup_checkbox` | Accepted on the sign-up form. |
| `checkout_step` | Accepted during checkout. |
| `sdk_api` | Accepted through the API. |
| `oauth_onboarding` | Accepted in the onboarding flow. |

The first four are the canonical methods. A fifth value is stored as it arrives, so a row can name a surface the product does not produce.

## Closing the organization

At the bottom of the page, a **Delete** button opens a **Delete organization**
dialog. The server accepts the request from the owner only. A request from
anyone else is refused.

To close an organization that still has other members, transfer ownership to
one of them first. The request is refused with `ORG_HAS_MEMBERS` and the
member count.

The dialog asks you to type the organization name. The **Delete organization**
button stays disabled until the name matches.

What closing the organization does:

- Marks the organization as closed. The workflows, policies, API keys, memberships and pending invites go with it. Alert channels stop delivering, the notification settings are dropped, and the Slack installation is revoked. Executions, traces, approval rules and alert rows stay until the purge.
- Leaves the audit rows in place. They are kept for the retention window so a forensic question can still be answered afterwards.
- Leaves the sessions alone. The owner keeps the browser session. An organization with other members is refused before this point, so no other member is signed out here.

### The 60-day grace period

A closed organization can be restored. The grace period is 60 days.

| Action | Effect |
|---|---|
| **Restore** | Puts the organization back in front of the gate. The spend counters for the period survive, so a restored organization does not get a second allowance. |
| **Transfer ownership** | Hands the organization to another member. The remaining members keep access. |

Both actions live on the API only. The control center has no button for
either one.

When the grace period ends, the data is purged. The restore route is `POST /api/v1/orgs/{org_id}/restore`, and the ownership transfer is `POST /api/v1/orgs/{org_id}/transfer-ownership`.

## Audit trail

The DPA acceptance is recorded in the audit log with the actor and the
timestamp. A name change, a contact email change, and closing the
organization write no row.

## See also

- [Team](team.md) — members, roles, and seats
- [Billing & Plan](billing.md) — the plan and the invoices
- [Profile settings](profile.md) — your own account
- [Audit log](error-handling.md#audit-trail) — what the control center records
