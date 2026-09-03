---
title: Billing & Plan
maturity: stable
description: The merged Billing & Plan page — two tabs (subscription / payment / invoices, and quota / plan comparison / feature availability) sharing one fetch and one loading state.
---

# Billing & Plan

The **Billing & Plan** page combines subscription / payment /
invoice history with quota / plan-comparison / feature-gate
information under one URL. It lives at
`/control-center/billing` in the sidebar.

Before the merge, these were two separate pages
(`/control-center/billing` and `/control-center/plan`) that
shared most of their data. The merged view avoids two round-trips
for the "should I upgrade and how do I pay" question the operator
actually has.

The active tab is encoded in the URL via `?tab=billing|plan` so the
view is shareable + reload-safe. `?tab=plan` is the common inbound
from upgrade prompts (the at-risk banner, the `TierGate`, the
legacy `/control-center/plan` URL which now redirects). Anything
else — and the default — is the **Billing** tab.

## The Billing tab

Default landing. The header reads **Billing** with the subtitle
"Subscription, payment method and invoice history."

The hero card surfaces:

- **Plan name + price** (e.g. `Starter · $49/mo · Renews Sep 30`).
- **Status pill** — `Active` / `Trialing` / `Past due`.
- **Manage subscription** button (opens the customer portal — see
  the migration note below).
- **Update payment method** button.

Below the hero:

- **Current period end** — RFC-3339 timestamp.
- **Payment method** — `Brand · last4` (Visa, Mastercard, Amex).
  Full PAN and CVC are never persisted; Polar is the merchant of
  record.
- **Invoice history** — table of `Date / Invoice number / Amount /
  Status / Download`. Each PDF download wraps the blob in
  `URL.createObjectURL` and opens it; `window.open` can't attach
  the bearer token.

!!! note "Customer portal retired"
    The Polar customer portal is no longer a product surface
    (2026-07-07). Both **Manage subscription** and **Update
    payment method** controls now render a `mailto:support@nullrun.io`
    deep-link with a pre-filled subject + body. Auto-checkout on
    first mount (when `pending_checkout_plan` is set in
    sessionStorage) is preserved.

### Lite orgs

Lite is the free tier — there is no `billing_subscriptions` row.
The hero reads `$0/mo · Free tier` and the payment-method /
invoices sections collapse.

## The Plan tab

Default landing when `?tab=plan` is set. The header reads **Plan**
with the subtitle "Quota usage, plan comparison and feature
availability."

The tab surfaces:

- **Quota usage cards** — every plan cap (workflows, policies,
  api_keys, seats, executions) with `used / limit` and a
  percentage. The executions card surfaces
  `executions_period_kind` so the operator knows whether the reset
  is **calendar_month UTC** (Lite) or the **Polar billing-cycle
  anchor** (paid plans) or the **lite_rolling_period**.
- **At-risk banner** — when `quota.at_risk` is true, the page
  renders a callout with the projected hit date
  (`projected_hit_in_days`) and a CTA to upgrade.
- **Plan comparison table** — every public plan catalog row, with
  the per-tier feature column (Approval rules, Audit log, MCP
  servers, Notifications, …). The current plan row is highlighted
  and disabled.
- **Per-tier feature-gate panel** — a tighter view of which
  features are on/off at the current plan, with upgrade CTAs.

The catalog comes from `GET /api/v1/plans`, which is
unauthenticated and lives outside the `createApiClient` factory,
so the page shell fetches it once and threads it through both
tabs.

### Billing period toggle

Above the comparison table, a `BillingPeriodToggle` switches
between **Monthly** and **Yearly** price columns. The yearly
column is computed via `computeYearlyPriceCents` so the discount
matches the public pricing page.

## Auto-checkout (post-signup)

When a user lands on `/control-center/billing` directly with a
`pending_checkout_plan` in sessionStorage (post-signup flow), the
Billing tab is the right destination — it shows the
**Manage subscription** portal button after a successful checkout
returns. The Plan tab doesn't get this side effect because the Plan
tab is a comparison, not a payment surface.

## Upgrading from anywhere

The same Billing & Plan page is where every upgrade prompt in the
dashboard lands. The redirect contract is:

- TierGate on a gated page → `?tab=plan`.
- At-risk banner (any page) → `?tab=plan`.
- `Upgrade plan` button in a feature empty-state → `?tab=plan`.

All three deep links land on the Plan tab so the user sees the
comparison table before being asked to pay.

## Where to read next

- [Pricing page](https://nullrun.io/pricing) — public plan
  catalog (the Billing page reads from the same endpoint).
- [Workspace & Org](organization.md) — for changing the org
  name / contact email / DPA acceptance.
