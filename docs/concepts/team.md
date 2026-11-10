---
title: Team
maturity: stable
description: The people in an organization — the four roles and what each one allows, how to invite someone, and how the seat quota works.
---

# Team

The **Team** page lists everyone in the organization, every invite that has not been accepted yet, and what each person is allowed to do.

The team feature is on Starter and above. On Lite the sidebar link is
hidden and the page shows an upgrade prompt.

## Roles

There are four roles. They are ranked: every role can do what the roles below it can do.

| Role | Can do |
|---|---|
| **Viewer** | Read the control center: workflows, executions, traces, the audit log, and API keys. Export the audit log is not included — that needs Operator. |
| **Operator** | Everything a Viewer can do, plus pause and kill workflows, decide approvals, simulate a policy, and export the audit log. |
| **Admin** | Everything an Operator can do, plus create and edit workflows, policies, API keys and approval rules, edit the organization, manage MCP servers, and invite and remove members. |
| **Owner** | Everything an Admin can do, plus change a member's role, manage billing and SSO, and delete the organization. |

An organization always has at least one owner. The last owner cannot be demoted or removed.

Role-based access control arrives on Growth. On Starter an admin has no
effective authority — the owner carries it alone.

## Inviting someone

1. Open **Team** in the sidebar.
2. Enter the person's email address.
3. Pick the role they should have.
4. Send the invite.

The invite arrives by email and points at `https://nullrun.io/invite?token=<token>`. The link works for 7 days and stays the same until the invite is accepted or revoked.

An invite that grants **Admin** needs an **Owner** to send it. An Admin can invite a Viewer or a Member. The server checks the sender's role when the invite is sent and again when it is accepted.

An invite is refused when:

- The address is already a member of the organization.
- An invite to that address is still pending.
- The seat quota is full.

One person can send 10 invites an hour. Past that the server refuses with a retry delay.

## Pending invites

Invites that have not been accepted are listed under the members. Each row shows the address, the role, the invite link, and whether the last delivery attempt succeeded. You can resend the invite or revoke it.

A revoked invite stops working immediately.

## Seat quota

The header shows how many seats the organization uses against the plan's allowance. The number on screen adds the pending invites to the members, so an outstanding invite shows its cost before it is accepted.

The server counts members only. It refuses a new invite when the members already fill the plan's allowance, and it refuses an invite at accept time when accepting it would fill the allowance. The two counts can disagree, so a pending invite is a reservation, not a guarantee.

When the quota is full, the invite button is disabled and the page links to **Billing & Plan** to buy more seats.

## Removing a member

Owners and admins can remove a member from the members list. Removing someone ends their sessions for the organization, so a live session cannot outlive the membership.

The last owner cannot be removed.

## Changing a role

Only an owner can change a member's role. Changing your own role is not possible, and the last owner cannot be demoted.

## Audit trail

On Growth and above, every invite, resend, revoke, role change, and removal is recorded in the audit log with the actor and the timestamp. Filter by the team action to reconstruct who did what.

The audit log is a plan feature. Lite and Starter have none.

## See also

- [Organization](organization.md) — the organization's name, contact email, and DPA acceptance
- [Billing & Plan](billing.md) — where seats are bought
- [Audit log](error-handling.md#audit-trail) — every team change leaves a row
