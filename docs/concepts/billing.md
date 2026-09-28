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
from upgrade prompts (the at-risk banner, the `TierGate`, and the
`/control-center/plan` URL, which redirects here). Anything
else — and the default — is the **Billing** tab.

## The Billing tab

Default landing. The header reads **Billing** with the subtitle
"Subscription, payment method and invoice history."

The hero card surfaces:

- **Plan name + price** (e.g. `Starter · $29/mo · Renews Sep 30`).
- **Status pill** — `Active` / `Past due` / `Cancelled` / `Expired`
  (4-state machine; `Trialing` is not a state — paid plans go
  straight to `Active` after Polar checkout; Lite is free forever
  with no trial).
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

!!! note "Customer portal"
    NullRun does not operate a self-service customer portal. Both
    **Manage subscription** and **Update payment method** controls
    render a `mailto:support@nullrun.io` deep-link with a pre-filled
    subject + body. Auto-checkout on first mount (when
    `pending_checkout_plan` is set in sessionStorage) is preserved.

### Lite orgs

Lite is the free tier — there is no active `billing_subscriptions`
row (a row in `Cancelled` or `Expired` status is also treated as
Lite: no Polar anchor, no live payment method). The hero reads
`$0/mo · Free tier` and the payment-method / invoices sections
collapse.

## The Plan tab

Default landing when `?tab=plan` is set. The header reads **Plan**
with the subtitle "Quota usage, plan comparison and feature
availability."

The tab surfaces:

- **Quota usage cards** — every plan cap (workflows, policies,
  api_keys, seats, executions, tokens/hour, requests/second,
  approval rules) with `used / limit` and a percentage. The
  executions card surfaces `executions_period_kind` so the operator
  knows whether the reset is the **Lite rolling 1-month window**
  anchored at `organizations.created_at` (Lite) or the **Polar
  billing-cycle anchor** (paid plans). `calendar_month` only
  appears as a Postgres-failure fallback when the org-row lookup
  fails.
- **At-risk banner** — when `quota.at_risk` is true, the page
  renders a callout with the projected hit date
  (`projected_hit_in_days`) and a CTA to upgrade.
- **Plan comparison table** — every public plan catalog row, with
  the per-tier feature column (Approval rules, Audit log, MCP
  servers, Notifications, …). The current plan row is highlighted
  and disabled.
- **Per-tier feature-gate panel** — a tighter view of which
  features are on/off at the current plan, with upgrade CTAs.

### Per-tier caps

Canonical cap values per plan (from the `plans` table — single
source of truth, surfaced via `GET /api/v1/plans`):

| Cap | Lite | Starter | Growth | Scale | Enterprise |
|---|---|---|---|---|---|
| Workflows | 3 | 8 | 50 | 200 | unlimited |
| API keys | 10 | 15 | 100 | 350 | unlimited |
| Seats | 1 | 3 | 10 | 75 | unlimited |
| Policies | 3 | 10 | 25 | 150 | unlimited |
| Approval rules | 0 | 0 | 20 | unlimited | unlimited |
| Tokens / hour | 10 000 | 25 000 | 300 000 | unlimited | unlimited |
| Executions / month | 75 000 | 100 000 | 750 000 | 2 000 000 | unlimited |
| Requests / second | 5 | 10 | 50 | 300 | 1 000 |

Lite has the `team`, `approvals`, and `audit log` features
disabled; Starter unlocks team workspaces and alerts; Growth
unlocks approvals, audit log, custom policies, and command
palette; Scale adds saved-cost-share and unlimited workflows;
Enterprise removes every cap.

The catalog comes from `GET /api/v1/plans`, which is
unauthenticated and lives outside the `createApiClient` factory,
so the page shell fetches it once and threads it through both
tabs.

### Billing period toggle

Above the comparison table, a `BillingPeriodToggle` switches
between **Monthly** and **Yearly** price columns. The yearly
column is computed via `computeYearlyPriceCents` so the discount
matches the public pricing page. The wire string for the yearly
period is `"year"` (not `"yearly"`) — `BillingPeriod::Yearly.as_str()`
returns the short form to match the frontend
`BillingData.billing_cycle: "monthly" | "year"` type.

!!! note "Plan IDs on the wire"
    The canonical id for Enterprise is `"enterprise_unlimited"`.
    The id `"enterprise"` carries Scale content. `GET /api/v1/plans`
    returns the canonical id; the dashboard renders it as the
    **Enterprise** plan name. If you query the catalog by id, use
    `enterprise_unlimited`.

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

!!! info "Deep dive"

    Plan identity and subscription state are both small state machines.
    A subscription is always in one of four states â€” active, past due,
    cancelled, or expired â€” and only a few moves between them are
    valid: active may go to past due, cancelled, or expired, and past
    due may go back to active or onwards to cancelled or expired.
    Anything else is rejected rather than coerced, so status never
    rewinds implicitly and a failed renewal cannot silently restore a
    cancelled plan. A free org has no subscription row at all, and that
    absence is what marks the free tier; a subscription sitting in
    cancelled or expired status counts as free too.

    Prices and capabilities are read from the plan catalog rather than
    embedded in the page, so the dashboard, the public pricing page,
    and any direct query against the catalog agree by construction. The
    catalog is readable without authentication and is cacheable, which
    is what lets the page shell fetch it once and share the result
    across both tabs. Yearly pricing is derived from the same monthly
    figure by a single computation, so the discount shown in the
    comparison table matches the public pricing page exactly.

    The Enterprise plan carries the wire identifier
    `enterprise_unlimited`. Query the catalog by that identifier; the
    shorter `enterprise` identifier does not name the Enterprise tier.
    Paid plans have no trial state â€” checkout moves a plan straight to
    active â€” and the free tier stays free indefinitely.

    There is no self-service customer portal and no self-service
    cancellation: both subscription management and payment-method
    updates resolve to a support contact, and an invoice is downloaded
    through a credentialed request rather than handed to a new window.
    Every upgrade entry point in the product â€” the prompt on a gated
    page, the at-risk banner, and the upgrade action in a feature empty
    state â€” deep-links to the Plan tab, so a comparison is always shown
    before a payment is requested. The Plan tab stays
    comparison-only; payment actions live on the Billing tab.
