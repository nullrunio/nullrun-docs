# Budgets

A **budget** is the most important number on the dashboard. It's the
maximum amount of money a workflow is allowed to spend in a billing
period. Set it too low and your agent stops working. Set it too high
and a runaway agent burns through real money before you notice.

This page covers what the budget controls, how the dashboard shows
it, and what happens at each boundary.

## Where you see it

On the **Workflows** detail page, the budget appears as a progress
bar near the top:

```
Spend this period         $47.30 of $50.00  (95%)
████████████████████████░░
Time to exhaustion         ~16 hours at current rate
```

Three numbers:

- **Spend this period** — total cents spent since the last period
  rollover. Resets automatically.
- **Budget** — the cap. Set this in workflow settings.
- **Time to exhaustion** — at the current rate of spend, when the
  budget will run out. Useful for "should I raise the cap?".

## What the budget covers

The budget covers **spend**, not calls. Calls are rate-limited
separately — see [Policies](policies.md).

"Spend" is calculated from token counts reported by your LLM
provider. The dashboard knows the per-model pricing for every model
the SDK tracks:

- **Input tokens** × input rate
- **Output tokens** × output rate
- **Cache read** / **cache write** tokens (if your provider exposes
  them) at their respective rates
- **Reasoning tokens** for o1/o3-style models at the reasoning rate

The total spend is the sum across all `@protect` calls inside the
workflow, across the current period.

## Periods

A "period" is the window after which the spend counter resets.
NullRun has two period sources:

| Plan | Period source | When it resets |
|---|---|---|
| **Lite** (free) | Calendar month UTC | 1st of each month at 00:00 UTC |
| **Paid** (Starter / Growth / Scale) | Your billing cycle (Polar subscription) | Set when you subscribed; on renewal |

The dashboard shows the period start and end dates next to the
spend bar. When the period rolls over, the spend counter resets to
zero and the budget applies fresh.

## What happens at the boundary

Three scenarios, depending on the workflow's [enforcement
mode](policies.md#budgetlimit-extra-fields):

### Hard mode (default)

```
Spending → $49.95 of $50.00
Next @protect call:        #2.00 projected
gate decision:             block
SDK raises:                 NullRunBudgetError (NR-B004, wire BUDGET_HARD_BLOCKED)
@guarded:                   prints friendly message, sys.exit(1)
```

The agent stops cleanly at the boundary. No partial charge — the
projected cost is reserved when the gate approves, and the actual
cost is reported after the LLM returns. If the call is denied, no
charge happens.

### Soft mode

Soft mode lets the agent run past its budget when an active chain is
present, up to the configured overdraft cap
(`max_overdraft_cents` or `max_overdraft_percent`, whichever is
lower). The chain returns to standard Hard mode once the cap is
exhausted. See [Policies → BudgetLimit extra fields](policies.md#budgetlimit-extra-fields)
for the full configuration contract.

## How to set the budget

The first time you create a workflow, no budget cap is configured.
`max_budget_cents == 0` means **"no per-key budget configured"** —
the gate passes through to the org-level plan cap, not "block
everything" — so the agent runs against the org's default policy
until you raise the per-key cap.

To set the budget:

1. Open the workflow.
2. Click **Settings**.
3. Find **Budget** and enter cents (`$50` = `5000`).
4. Save.

Reasonable starting budgets:

| Use case | Suggested budget |
|---|---|
| Personal / dev experiment | $5 (500 cents) per period |
| Single-tenant internal tool | $20 (2000 cents) per period |
| Customer-facing AI feature | $100 (10000 cents) per period, plus an alert at 80% |

The dashboard warns you when spend crosses 80% of the cap and again
at 100%. Configure alert destinations under **Settings →
Notifications**.

## What happens when you change the budget mid-period

- **Raise**: the new cap takes effect immediately. The next gate
  call uses the new cap.
- **Lower below current spend**: the agent doesn't get retroactive
  refunds, but every call from this point onward rejects until the
  spend drops (which only happens at period rollover, since the
  counter is monotonic within a period).

## Why cents, not dollars

The dashboard stores everything in cents to avoid floating-point
rounding in pricing math. The `budget_cents` field in the API is
always an integer. If you set `budget_cents: 5000`, your cap is
exactly $50.00, no rounding errors.

## Reservation and consumption

The budget interaction splits into two phases:

1. **`/api/v1/gate` reservation** — before execution. The gate
   computes the projected cost from `estimated_tokens`, atomically
   reserves it in Redis (TTL 300s), and returns `allow` / `block` /
   `require_approval`.
2. **`/api/v1/track` consumption** — after the LLM returns. The
   SDK reports the actual cost. The reservation is consumed and the
   period counter is incremented.

The two phases share an **invariant**: `actual_cost ≤ reserved + ε_cents`
with `ε_cents = 1` by default. If the SDK reports a larger cost,
`/track` returns `422 CONSUME_OVERBUDGET` (fail-CLOSED — no implicit
re-reserve).

The `/track` ingestion goes through a Postgres outbox. The Redis
authoritative counter is updated synchronously; the Postgres
`cost_events` row is drained asynchronously. A Postgres outage
does not block the inference — events stay in the outbox pending
and drain when Postgres recovers (retry × 5, exponential backoff to
16s, then `dead_letter` with 30-day retention).

## See also

- [Workflows](workflow.md) — where the budget lives
- [Policies](policies.md) — rate limits (separate from budget) and soft-mode fields
- [Troubleshooting](../troubleshooting.md#why-is-my-call-being-rejected-with-nullrunblockedexception)
