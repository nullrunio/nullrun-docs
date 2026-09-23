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

## Deep dive

!!! info "Deep dive"

    The billing surface lives in `backend/src/billing/`. The
    `BillingPlan` enum (`backend/src/billing/models.rs`) is the
    canonical plan identifier — `Lite | Starter | Growth | Scale |
    EnterpriseUnlimited`, with `enterprise_unlimited` as the
    canonical id for the Enterprise tier. The legacy `enterprise`
    string was reclaimed by migration 030 to carry Scale content;
    the real Enterprise tier lives under `enterprise_unlimited`
    in the `plans` table. Subscription lifecycle is driven by
    `SubscriptionStatus` (`models.rs`) — 4-state machine `Active
    | PastDue | Cancelled | Expired`. State transitions are
    gated by `can_transition_to`: only `Active → {PastDue,
    Cancelled, Expired}` and `PastDue → {Active, Cancelled,
    Expired}` are valid. `Lite` is the implicit pre-checkout
    state (no `billing_subscriptions` row). Polar integration is
    in `backend/src/billing/polar.rs`; webhook signature
    verification (`verify_webhook_signature`) uses
    `t=<ts>,v1=<hex_hmac>` HMAC-SHA256 with a 5-minute replay
    window.

    The Polar customer portal is NOT a product surface:
    `create_customer_session` was removed 2026-07-07
    (`provider.rs` note, `polar.rs`); both **Manage
    subscription** and **Update payment method** controls render
    a `mailto:support@nullrun.io` deep-link with a pre-filled
    subject + body. Auto-checkout on first mount is preserved
    when `pending_checkout_plan` is set in sessionStorage. There
    is no `Trialing` state — paid plans go straight to `Active`
    after Polar checkout; Lite is free forever with no trial. The
    subscription state machine is strict — invalid transitions
    fail at `can_transition_to`; no implicit re-billing or status
    rewind. ADR-039 wires yearly pricing: `BillingPeriod` enum
    carries `"year"` / `"month"` end-to-end; the wire string is
    `"year"` to match the frontend
    `BillingData.billing_cycle: "monthly" | "year"` type.
    ADR-039 also wires `yearly_price_cents` from the `plans`
    table — no hard-coded literals. ADR-057 Lite Trial overlay:
    mid-trial Lite orgs get Scale-equivalent caps
    (`executions_limit`, `policies_limit`, etc.) without
    changing `organizations.plan_id`.
    `is_trial_active(started, expires, now)` is the resolver
    invariant (`trial_bundle.rs`); `activate_subscription_atomic`
    clears the trial in-tx (`db/mod.rs`). Deploy-day gated by
    `NULLRUN_LITE_TRIAL_ENABLED=1`.

    Single source of truth = `plans` table: both `price_cents`
    and `polar_id` are read at runtime via
    `Database::get_plan_config(plan)` (`models.rs`); no
    hard-coded literals in code. `GET /api/v1/plans` is
    unauthenticated and cacheable: used by both the dashboard
    shell and the public pricing page. The endpoint lives
    outside `createApiClient` so the page shell fetches it once
    and threads it through both tabs. The canonical upgrade-
    prompt redirect is `TierGate → ?tab=plan`: TierGate on a
    gated page, the at-risk banner on any page, and the
    `Upgrade plan` button in a feature empty-state all deep-link
    to `?tab=plan`. Yearly prices are computed client-side:
    `computeYearlyPriceCents` matches the public pricing page;
    the wire value `billing_cycle: "year"` matches the backend
    `BillingPeriod::Yearly.as_str()`.

    The customer portal was retired because the Polar "cancel"
    button always lost paid users (the portal didn't surface
    what NullRun charged or why). Removing it forces
    payment/cancel decisions to `mailto:support@nullrun.io`,
    where support can route around churn rather than losing the
    relationship to a vendor UI. The merge of `/billing` and
    `/plan` into a single URL with `?tab=` came from the
    operator pattern of asking "should I upgrade and how do I
    pay" — two pages meant two round-trips for the same
    decision. The Plan tab is comparison-only; the Billing tab
    carries the action surface. Anything that looks like a
    payment decision deep-links to Billing. The `enterprise` id
    reclaim by migration 030 was a deliberate choice — the
    legacy `enterprise` id was reused rather than deprecated to
    avoid an old `subscription` row pointing at a now-missing
    plan id (which would block `current_period_end`
    calculations). New rows must use `enterprise_unlimited`;
    old rows still resolve correctly because the `plans` table
    carries the id mapping.

    No self-service cancel: cancel is a `mailto:support@nullrun.io`
    deep-link — `Manage subscription` no longer opens a portal.
    No customer-side invoice-management portal: invoice
    downloads are wrapped in `URL.createObjectURL` blobs
    because `window.open` cannot carry the bearer token. The
    `enterprise` id on the wire carries Scale content: only
    `enterprise_unlimited` is the canonical Enterprise id;
    operators querying by id must use the canonical form.
    ADR-057 trial overlay is deploy-day gated: the code is
    shipped (`98df0e5b` local commit) but
    `NULLRUN_LITE_TRIAL_ENABLED=1` must be flipped before the
    overlay takes effect for new signups — pre-flip, Lite
    signups get the canonical Lite caps.
