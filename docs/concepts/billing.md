---
title: Billing & Plan
maturity: stable
description: The plan an organization runs on — its caps, its features, the period the usage counter resets on, and where to read the spend.
---

# Billing & Plan

The **Billing & Plan** page covers two things: the subscription and the plan. It lives under **Account** in the sidebar and has two tabs.

| Tab | Answers |
|---|---|
| **Billing** | Which plan, at what price, paid how, with which invoices. |
| **Plan** | How much of the plan is used, and what a different plan gives. |

The tab is part of the URL: `?tab=billing` or `?tab=plan`. **Billing** is the default. Every upgrade prompt in the control center opens `?tab=plan`, so a comparison comes before a payment.

## Plans and prices

| Plan | Monthly | Yearly | Per month, billed yearly |
|---|---|---|---|
| Lite | $0 | — | — |
| Starter | $29 | $278 | $23 |
| Growth | $99 | $950 | $79 |
| Scale | $299 | $2 870 | $239 |
| Enterprise | Contact sales | Contact sales | Contact sales |

Yearly billing costs 20 % less than twelve monthly payments. Lite is free and has no paid cycle.

## What a plan includes

A plan sets two things: the caps on what an organization may create, and the features it may use.

### Caps

| Cap | Lite | Starter | Growth | Scale | Enterprise |
|---|---|---|---|---|---|
| Executions per month | 75 000 | 100 000 | 750 000 | 2 000 000 | Unlimited |
| Workflows | 3 | 8 | 50 | 200 | Unlimited |
| Policies | 3 | 10 | 25 | 150 | Unlimited |
| API keys | 10 | 15 | 100 | 350 | Unlimited |
| Seats | 1 | 3 | 10 | 75 | Unlimited |

An approval rule counts against the policy cap. A policy that carries its own approval rule counts once, as a policy.

### Features

| Feature | Lite | Starter | Growth | Scale | Enterprise |
|---|---|---|---|---|---|
| Team | — | Yes | Yes | Yes | Yes |
| Alerts | — | Yes | Yes | Yes | Yes |
| RBAC | — | — | Yes | Yes | Yes |
| Human approvals | — | — | Yes | Yes | Yes |
| Audit log | — | — | Yes | Yes | Yes |
| Custom policies | — | — | Yes | Yes | Yes |
| Replay | — | — | Yes | Yes | Yes |
| SSO | — | — | — | Yes | Yes |
| History retention | 3 days | 7 days | 30 days | 90 days | Unlimited |

## The Lite trial

A new Lite organization gets Scale for 14 days. The Plan tab shows a countdown while the trial runs and a banner when it ends. The organization keeps its Lite plan and its Lite caps when the trial ends.

## The period

The executions counter runs over a period, and the period decides when the counter resets.

| Plan | The period |
|---|---|
| Lite | A rolling 30 days, anchored at the day the organization was created. |
| Paid | The billing cycle. Monthly or yearly, as billed. |

The Plan tab states the period under the Executions card: `rolling 30 days · resets in N days` for Lite, `resets on your billing day · in N days` for a paid plan.

## Reading the usage

The Plan tab opens with five quota cards, one per counter.

| Card | Counts | Resets |
|---|---|---|
| Executions | The decisions the organization took in the period. | On the period boundary. |
| Workflows | Saved workflows. | Never. |
| API keys | API keys. | Never. |
| Policies | Policies, plus the approval rules that count against the policy cap. | Never. |
| Team members | Members and pending invites. | Never. |

Each card shows the count, the cap, and the share used. A card with room left shows `N remaining`. A card on an unlimited cap shows `Unlimited`.

Deleting a workflow, a policy, or an API key frees its slot at once.

### The at-risk banner

When the organization is on pace to reach its execution cap before the period ends, a banner states the number of days and links to a larger plan. Once the cap is reached, every execution is refused until the period resets.

## The plan comparison table

The Plan tab carries a table with one column per plan and one row per cap or feature: Price, Executions per month, Workflows, Policies, API keys, Seats, Team, RBAC, Human approvals, Audit log, History. The current plan's column is marked, and its button is disabled.

A **Monthly** / **Yearly** toggle sits above the table. It switches the price row between the monthly and the yearly figure.

## The Billing tab

### The plan card

The card names the plan and the price.

| Plan | Reads |
|---|---|
| Lite | `Free • Forever`, with a **Free tier** chip. |
| Paid | `$29/mo` or `$278/yr`, with an **Active subscription** chip. |

A paid organization on the monthly cycle also gets a **Save 20 %** banner that links to the yearly prices.

### Subscription details

| Field | Meaning |
|---|---|
| Status | `active`, `past_due`, `cancelled`, or `expired`. |
| Subscription ID | The short identifier of the subscription. |
| Started | The day the subscription began. |
| Next renewal | The day the current period ends. |

A Lite organization has no subscription, and the card reads **No active subscription**.

### Payment method

The card shows the card on file as `Brand •••• last4`. **Update payment method** opens an email to support.

### Invoices

The invoice table has one row per invoice.

| Column | Meaning |
|---|---|
| Date | When the invoice was issued. |
| Invoice | The invoice number. |
| Amount | The amount charged. |
| Status | `paid`, `open`, or `pending`. |
| Download | The invoice PDF. |

An organization with no invoices reads **No invoices yet**.

### Contacting support

NullRun has no self-service customer portal. **Contact support** and **Update payment method** both open an email to `support@nullrun.io` with the details filled in.

## Changing the plan

**Upgrade plan** on the plan card opens the Plan tab, where each other tier carries its own button. An upgrade takes effect at once.

A downgrade to a plan with lower caps asks what to do with the objects that no longer fit. The preview lists every group that is over its new cap.

| Group | Choice |
|---|---|
| Workflows | Archive, Delete, or Keep. |
| Policies | Archive, Delete, or Keep. |
| Members | Archive. |
| Slack installs | Archive. |
| API keys | Revoke. |

A downgrade takes effect at the end of the current billing period. The Plan tab shows a banner with the date and the target plan until then.

## Plan identifiers

The plan identifiers on the wire are `lite`, `starter`, `growth`, `scale`, and `enterprise_unlimited`.

| Plan | Identifier |
|---|---|
| Lite | `lite` |
| Starter | `starter` |
| Growth | `growth` |
| Scale | `scale` |
| Enterprise | `enterprise_unlimited` |

Query the plan catalog by `enterprise_unlimited` for the Enterprise tier.

## API

The plan catalog is public. It needs no authentication.

| Method | Path |
|---|---|
| `GET` | `/api/v1/plans` |

## See also

- [Budgets](budgets.md) — the money the plan pays for
- [Team](team.md) — the seats the plan carries
- [Organization](organization.md) — the workspace the plan belongs to
