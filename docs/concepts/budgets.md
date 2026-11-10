---
title: Budgets
maturity: stable
description: Hard and soft budget enforcement, the billing period that resets the spend counter, and the reserve-and-consume rule behind every cent.
---

# Budgets

A **budget** is the maximum amount of money a workflow may spend in one
billing period. Set it too low and your agent stops working. Set it
too high and a runaway agent burns real money.

Amounts are always in **cents**. `$50.00` is `5000`.

## Which cap binds

Two caps can apply to the same workflow:

| Cap | Where it comes from | Counter it is measured against |
|---|---|---|
| Org ceiling | A `BudgetLimit` policy with scope **Org** | One counter shared by every workflow in the organization |
| Workflow ceiling | A `BudgetLimit` policy with scope **Workflow** | One counter per workflow |

Both apply. The control center shows the smaller of the two as the
effective cap. The org ceiling is **always strict** — it is enforced
even when the workflow's own policy uses Soft mode.

A workflow with no `BudgetLimit` policy of its own has no workflow
ceiling. The org ceiling still applies to it.

## Where you see it

The **Budget** card on a workflow's **Overview** tab shows the spend
for the current period against the effective cap, a progress bar, and
a caption that names where the cap came from.

<figure class="nr-shot">
  <img class="nr-shot__light" src="../../assets/images/screenshots/workflow-detail-light.png"
       alt="Workflow detail — Overview tab. The Budget card sits at the top showing spent / cap."
       loading="lazy" decoding="async">
  <img class="nr-shot__dark" src="../../assets/images/screenshots/workflow-detail-dark.png"
       alt="Workflow detail — Overview tab. The Budget card sits at the top showing spent / cap."
       loading="lazy" decoding="async">
  <figcaption class="nr-shot__caption">Workflows · Budget card</figcaption>
</figure>

## What the budget covers

The budget covers **spend**, not calls. Calls are rate-limited
separately — see [Policies](policies.md).

"Spend" is calculated from the token counts your LLM provider reports
and the per-model prices the gateway holds:

- **Input tokens** × input rate
- **Output tokens** × output rate
- **Cache read** and **cache write** tokens, at their own rates
- **Reasoning tokens**, at the reasoning rate

The total is the sum across every `@protect` call for the current
calendar month.

## Periods

The **spend counter** the gate enforces against resets on the **first of
every month, UTC**. The period comes from the server, not from your
agent, and it is the same window for every plan.

The control center reports spend over a **reporting window**, which can
be a different one:

| Org | Reported window | When it resets |
|---|---|---|
| Paid | The billing cycle | On renewal |
| Lite | A rolling month anchored at signup | One month after signup, then every month after that |
| No billing cycle and not Lite | The UTC calendar month | On the first of the month |

Because the two windows can differ, the number on a report and the
number the gate enforces against are not always the same. The gate is
the authority.

## What happens at the boundary

Two scenarios, depending on the workflow's
[enforcement mode](policies.md#budgetlimit-extra-fields).

### Hard mode

```
Spending → $49.95 of $50.00
Next @protect call:        #2.00 projected
gate decision:             block
SDK raises:                 NullRunBudgetError (NR-B004)
with nullrun.guard():     prints the developer report, sys.exit(1)
```

The agent stops at the boundary. The projected cost of the call is
reserved while the gate approves it, and the actual cost is booked
after the LLM returns. A refused call is never charged.

### Soft mode

Soft mode lets the agent run past its workflow ceiling while an
active chain exists, up to a bounded overdraft. It needs the policy
to be scoped to a workflow, an active chain, and headroom under both
overdraft caps. If one is missing, the budget behaves as Hard.

The org ceiling still applies in Soft mode.

See
[Policies → Soft mode requirements](policies.md#soft-mode-requirements).

## Reserve and consume

The gate reserves the projected cost of a call, then books the actual
cost once the call returns. Three rules hold:

- The counter is **period-bound**. The period comes from the server
  and is fixed for the call, so a reservation and the later booking
  always land in the same period.
- The amount is in **cents**. No floating point, no rounding drift.
- The booking may exceed the reservation by a **fixed-cent epsilon**
  only. The default is 1¢, and each policy can set its own
  `consume_epsilon_cents`. A percentage epsilon is not supported.

An actual cost above the reservation plus the epsilon is **rejected**:
the commit returns HTTP **422** with the wire code
`CONSUME_OVERBUDGET`, and the SDK raises
`NullRunConsumeOverbudgetError` (`NR-O001`). The call is never
silently re-reserved. The period counter still shows the real spend.

A transport retry does not double-charge. The SDK mints one
`operation_id` for a logical action and carries it across the
reserve, the approval check and the booking. A repeated booking with
the same id replays the original response instead of charging again.

## How to set the budget

The cap comes from a budget policy:

1. Open **Governance → Policies → New policy**.
2. Pick the type **Budget**.
3. Pick the scope — **Organization** for a ceiling on the whole
   organization, or one **Workflow** for a cap on that workflow alone.
4. Fill **Max cost (USD/month)**. `$50.00` is `5000` cents.
5. Save. The policy is active immediately.

The steps for every policy type are in
[Policies → How to create one](policies.md#how-to-create-one).

A policy always carries a positive cap. The server rejects a
`budget_cents` of `0`. To remove a cap, deactivate or delete the
policy.

## When you change the budget mid-period

- **Raise** — the new cap applies to the next gate call.
- **Lower below the current spend** — no refund is issued. Calls are
  refused until the period rolls over, because the counter does not go
  down inside a period.

## Getting alerts

Spend alerts fire at three fixed points on the organization's running
spend: 80%, 95% and 100% of the threshold your plan carries. The ladder
and the channels are in
[Alerts → The budget ladder](alerts.md#the-budget-ladder).

## Approximate budget endpoint

To show "you have used X of Y" in your own report or a
notification, the gateway exposes an approximate-spend endpoint:

```bash title="shell"
curl -sS "https://api.nullrun.io/api/v1/budget/approximate" \
  -H "X-API-Key: ${NULLRUN_API_KEY}"
```

The response carries:

| Field | Meaning |
|---|---|
| `org_id` | The organization the key belongs to |
| `current_spend_cents_estimate` | Estimated spend for the current period, in cents |
| `is_approximate` | Always `true` |
| `source` | Where the number came from: `redis_period`, `postgres_outbox` or `last_known_redis` |
| `confidence` | `high`, `medium` or `low` |
| `last_updated_at` | ISO-8601 UTC timestamp of the read |

**Use this for display only.** Never for enforcement, rate-limit logic
or agent-side gating. When no source is available the endpoint returns
**503** with `error_code = "BUDGET_DATA_UNAVAILABLE"`. Render that as
"data unavailable", never as `≈ $0 spent` — a missing figure and an
empty one are different claims.

## See also

- [Workflows](workflow.md) — where the budget lives
- [Policies](policies.md) — rate limits and the soft-mode fields
- [Error handling](error-handling.md) — the exception each refusal
  raises
- [Troubleshooting](../troubleshooting.md#the-call-is-rejected-with-nullrunblockedexception)
