---
title: Budgets
maturity: stable
description: Hard and soft budget enforcement, billing-period rollover, and the reserve-and-consume rule that keeps a single call from being charged twice.
---

# Budgets

A **budget** is the maximum amount of money a workflow may spend in
one billing period. Set it too low and your agent stops working. Set
it too high and a runaway agent burns through real money.

Amounts are always in **cents**. `$50.00` is `5000`.

## Where you see it

On the **Workflows** detail page, the budget appears as a progress
bar near the top:

```
Spend this period         $47.30 of $50.00  (95%)
████████████████████████░░
Time to exhaustion         ~16 hours at current rate
```

Three numbers:

- **Spend this period** — cents spent since the period started. It
  resets automatically.
- **Budget** — the cap. Set this in workflow settings.
- **Time to exhaustion** — at the current rate of spend, when the
  budget runs out.

## What the budget covers

The budget covers **spend**, not calls. Calls are rate-limited
separately — see [Policies](policies.md).

"Spend" is calculated from the token counts your LLM provider reports
and the per-model prices the gateway holds:

- **Input tokens** × input rate
- **Output tokens** × output rate
- **Cache read** and **cache write** tokens, at their own rates
- **Reasoning tokens**, at the reasoning rate

The total is the sum across every `@protect` call in the workflow, for
the current period.

## Periods

A **period** is the window after which the spend counter resets. The
period comes from the server, not from your agent.

| Plan | Period source | When it resets |
|---|---|---|
| **Lite** (free) | Rolling one-month window anchored at signup | One month after signup (signed up Jun 15 → resets Jul 15, Aug 15, …) |
| **Paid** (Starter / Growth / Scale) | Your billing cycle | On renewal |

The dashboard shows the period start and end dates next to the spend
bar. When the period rolls over, the counter resets to zero and the
budget applies fresh.

## What happens at the boundary

Three scenarios, depending on the workflow's [enforcement
mode](policies.md#budgetlimit-extra-fields).

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

Soft mode lets the agent run past its budget when an active chain is
present, up to the configured overdraft cap
(`max_overdraft_cents` or `max_overdraft_percent`, whichever is
lower). The chain returns to Hard mode once the cap is exhausted. See
[Policies → BudgetLimit extra fields](policies.md#budgetlimit-extra-fields).

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
- A retry is safe. The reservation and the later booking are both
  idempotent, so a retried call reuses the stored result instead of
  charging twice.

An actual cost above the reservation plus the epsilon is **rejected**:
the commit returns HTTP **422** with the wire code
`CONSUME_OVERBUDGET`, and the SDK raises
`NullRunConsumeOverbudgetError` (`NR-O001`). The call is never
silently re-reserved. The period counter still shows the real
spend.

## How to set the budget

A new workflow has no budget cap. A cap of `0` means **no
per-workflow budget is configured** — the call passes through to the
org-level plan cap. It does not mean "block everything".

To set the budget:

1. Open the workflow.
2. Click **Settings**.
3. Find **Budget** and enter cents (`$50` = `5000`).
4. Save.

<figure class="nr-shot">
  <img class="nr-shot__light" src="../../assets/images/screenshots/workflow-detail-light.png"
       alt="Workflow detail — Overview tab. The Budget card sits at the top showing spent / cap."
       loading="lazy" decoding="async">
  <img class="nr-shot__dark" src="../../assets/images/screenshots/workflow-detail-dark.png"
       alt="Workflow detail — Overview tab. The Budget card sits at the top showing spent / cap."
       loading="lazy" decoding="async">
  <figcaption class="nr-shot__caption">Workflows · Budget card</figcaption>
</figure>

Reasonable starting budgets:

| Use case | Suggested budget |
|---|---|
| Personal / dev experiment | $5 (500 cents) per period |
| Single-tenant internal tool | $20 (2000 cents) per period |
| Customer-facing AI feature | $100 (10000 cents) per period, plus an alert at 80% |

The dashboard warns you when spend crosses 80% of the cap and again
at 100%. Configure alert destinations under **Notifications** in the
sidebar.

## What happens when you change the budget mid-period

- **Raise** — the new cap applies to the next gate call.
- **Lower below current spend** — no refund is issued. Every call
  from that point is refused until the period rolls over, because the
  counter does not go down inside a period.

## Approximate budget endpoint

To show "you have used X of Y" in a custom dashboard or a
notification, the gateway exposes an approximate-spend endpoint:

```bash title="shell"
curl -sS "https://api.nullrun.io/api/v1/budget/approximate" \
  -H "Authorization: Bearer ${NULLRUN_API_KEY}"
```

The response carries:

| Field | Meaning |
|---|---|
| `org_id` | The organization the key belongs to |
| `current_spend_cents_estimate` | Estimated spend for the current period, in cents |
| `is_approximate` | Always `true` |
| `source` | Where the number came from: `redis_period`, `postgres_outbox`, `last_known_redis` or `ui_local_cache` |
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
