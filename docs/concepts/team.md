---
title: Team
maturity: stable
description: The people in an organization — the roles and what each one allows, how to invite someone, and how the seat quota works.
---

# Team

The **Team** page lists everyone in the organization, every invite that has not been accepted yet, and what each person is allowed to do.

The team feature is on Starter and above. On Lite the sidebar entry carries a lock, and the page shows an upgrade prompt.

## Roles

A member holds one of four roles. They are ranked: every role can do what the roles below it can do.

| Role | Can do |
|---|---|
| **Viewer** | Read the control center: workflows, executions, traces, the audit log, and API keys. |
| **Member** | Read the control center. Cannot change the organization. |
| **Admin** | Everything a Member can do, plus create and edit workflows, policies, API keys and approval rules, edit the organization, manage MCP servers, and invite and remove members. |
| **Owner** | Everything an Admin can do, plus change a member's role, manage billing and SSO, and delete the organization. |

An organization always has at least one owner. The last owner cannot be demoted or removed.

Admin authority needs the RBAC plan feature, and that arrives on Growth. On Starter an admin has no effective authority — the owner carries it alone.

## Inviting someone

1. Open **Team** in the sidebar.
2. Enter the person's email address.
3. Pick the role they should have.
4. Click **Send invite**.

The invite arrives by email and points at `https://nullrun.io/invite?token=<token>`. The link works for 7 days.

An invite can grant **Viewer**, **Member**, or **Admin**. Ownership moves through a transfer, never through an invite. An invite that grants **Admin** needs an **Owner** to send it. The server checks the sender's role when the invite is sent and again when it is accepted.

An invite is refused when:

- An invite to that address is still pending.
- The seat quota is full. The refusal carries the seat count and the plan allowance.

One person can send 10 invites an hour. Past that the server refuses with a retry delay.

## Pending invites

Invites that have not been accepted are listed under the members. Each row shows the address, the role, the time left before expiry, and the email delivery status. You can copy the invite link, resend the invite, or revoke it.

A resend issues a new link and starts the 7-day window again. The old link stops working.

A revoked invite stops working immediately.

## Seat quota

The header shows how many members the organization has and how many seats the plan allows. A separate banner appears when the seats run out, and it counts the pending invites against the members, so an outstanding invite shows its cost before it is accepted.

The server counts members only. It refuses a new invite when the members already fill the plan's allowance, and it refuses an invite at accept time when accepting it would fill the allowance. The two counts can disagree, so a pending invite is a reservation, not a guarantee.

## Removing a member

Owners and admins can remove a member from the members list. Removing someone ends their sessions for the organization, so a live session cannot outlive the membership.

The last owner cannot be removed.

## Changing a role

Only an owner can change a member's role. Changing your own role is not possible, and the last owner cannot be demoted.

## Audit trail

Team changes leave no audit row. The audit log holds gate decisions and the changes to policies and workflows. It has no team filter.

## See also

- [Organization](organization.md) — the organization's name, contact email, and DPA acceptance
- [Billing & Plan](billing.md) — where seats are bought
- [Audit log](error-handling.md#audit-trail) — what the control center records
