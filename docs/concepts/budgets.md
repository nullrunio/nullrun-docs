title: Budgets
maturity: stable
description: Hard and soft budget enforcement, billing-period rollover, and the reserve / consume invariant that protects against implicit re-reservation.
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
| **Lite** (free) | Rolling 1-month window anchored at `organizations.created_at` | One month after signup (e.g. signed up Jun 15 → resets Jul 15, Aug 15, …) |
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
SDK raises:                 NullRunBudgetError (NR-B004)
with nullrun.handle():     prints the 4-line dev report, sys.exit(1)
```
<figcaption>Hard mode — the projected cost of the next call exceeds the remaining budget. The gate returns `block` before the model runs.</figcaption>

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

<figure class="nr-shot">
  <img class="nr-shot__light" src="../../assets/images/screenshots/workflow-detail-light.png"
       alt="Workflow detail — Overview tab. The Budget card sits at the top showing spent / cap.">
  <img class="nr-shot__dark" src="../../assets/images/screenshots/workflow-detail-dark.png"
       alt="Workflow detail — Overview tab. The Budget card sits at the top showing spent / cap.">
  <figcaption class="nr-shot__caption">Workflows · Budget card</figcaption>
</figure>

Reasonable starting budgets:

| Use case | Suggested budget |
|---|---|
| Personal / dev experiment | $5 (500 cents) per period |
| Single-tenant internal tool | $20 (2000 cents) per period |
| Customer-facing AI feature | $100 (10000 cents) per period, plus an alert at 80% |

The dashboard warns you when spend crosses 80% of the cap and again
at 100%. Configure alert destinations under **Notifications** in
the sidebar (Channels + Alert rules + Event subscriptions matrix).

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

The gate reserves your projected cost before the model runs and
reconciles the actual cost after. If the LLM call returns a cost
that meaningfully exceeds the reservation, the `/track` commit
rejects with `CONSUME_OVERBUDGET` (HTTP **422**, `error_code = "NR-O001"`) — no implicit re-reserve, ever. The tolerance is a
fixed cents value (`policies.consume_epsilon_cents`, default **1¢**);
no percentage-based epsilon is supported.

## Approximate budget endpoint

If you want to show "you've used X of Y" in a custom dashboard or
notification without enrolling in the full NullRun dashboard, the
gateway exposes an approximate-spend endpoint:

```bash title="shell"
curl "https://api.nullrun.io/api/v1/budget/approximate" \
  -H "Authorization: Bearer ***"
```

The response carries `current_spend_cents_estimate`, an
`is_approximate: true` flag, a `source` field, a `confidence` level
(`High` / `Medium` / `Low`), and `last_updated_at`. **Use this for
display only** — never for enforcement, rate-limit logic, or
agent-side gating. When the source is unavailable the endpoint
returns `503 BUDGET_DATA_UNAVAILABLE`; render that as "data
unavailable", never as `≈ $0 spent`.

## See also

- [Workflows](workflow.md) — where the budget lives
- [Policies](policies.md) — rate limits (separate from budget) and soft-mode fields
- [Troubleshooting](../troubleshooting.md#why-is-my-call-being-rejected-with-nullrunblockedexception)

## Deep dive

!!! info "Deep dive"

    The authoritative counter is `org:{id}:bp:{period_start_ts}:cost_cents`
    in Redis (mirrored by `:cost_millicents` for sub-cent precision per
    DEF-07-02), with `period_start_ts` computed server-side by
    `compute_calendar_month_period` and passed to `reserve_v3.lua` as
    `ARGV[21]` / `ARGV[22]` (ADR-026 / v3.64) — the script reads
    `redis.call('TIME')` for `now` but trusts the backend-computed
    period so no `2629800` approximation runs in the production path.
    `/track` flows through `consume_v3.lua`, which parses the
    `cjson.encode`d reservation record from `budget:reserved:{org}:{exec}`
    to recover `authorized_cents` and compares `actual` against
    `authorized + epsilon_cents` (fixed cents, default 1¢ — ADR-005); on
    `actual > authorized + ε` the script INCRBYs the period counter on
    actual spend, DELs the envelope, stamps
    `consumed_at = "overage_unreconciled"` + `status = "overage"`, and
    returns `CONSUME_OVERBUDGET` (HTTP 422). The 4-table audit separation
    (ADR-009) keeps the period counter in Redis for fast enforcement
    while `cost_events` flows through the Postgres outbox for durable
    history; the `ApproximateBudget` endpoint at
    `backend/src/proxy/http/budget.rs` walks Redis → Postgres outbox →
    last-known cache and returns 503 `BUDGET_DATA_UNAVAILABLE` (5s
    `Retry-After`) when all three miss.

    The reserve / consume pair is atomic in Lua: `reserve_v3.lua` HSETs
    `reserved_cents` on the binding before the period INCRBY so a retry
    between Lua return and Rust outbox commit sees `status='reserved'`
    and returns `{prior_cents, "OK", "REPLAY"}` instead of double-INCRBY
    (AUDIT P0-05), and `/track` idempotency keys on the binding's
    `status` field (`consumed` → `IDEMPOTENT_REPLAY`; `overage` →
    `CONSUME_OVERBUDGET` with the same 5-tuple the first call produced).
    The aggregator at `backend/src/proxy/policy_cache.rs::aggregate_policies_with_mode`
    runs `min()` over `budget_cents` across both scopes but stores the
    wf-only and org-only minima independently (`wf_budget_cents`,
    `policy_org_ceiling_cents`); Lua §6a enforces the always-strict
    org ceiling first, §5.5 pre-computes the wf ceiling state, and §6
    enforces it (Hard mode) or inside the soft-pass branch (Soft mode,
    gated on `enforcement_mode=Soft` + active `chain_id` + projected
    within `max_overdraft_cents` AND `max_overdraft_percent`). N
    concurrent chains share one org overdraft counter — they do NOT
    multiply the cap.

    The pre-ADR-026 path computed the period inside Lua via
    `HGET polar:{org}` and a `2629800`-month approximation and was
    REMOVED (ADR-026 / v3.64) because pre-ADR-026 callers could land
    on different period buckets across `/gate` and `/track` for the
    same execution (e.g. gate at 23:59:59, track at 00:00:01); the
    binding-as-source-of-truth path eliminates that drift. The
    `ApproximateBudget` three-tier fallback (Redis → Postgres →
    last-known) was chosen over a single source because Redis can be
    unavailable during a period rollover and Postgres outbox lag is
    sub-second to ~2s — three confidence bands (`High` / `Medium` /
    `Low`) let the UI render the value with the right caveat.
    Percentage ε was considered and rejected (ADR-005 §"Why fixed
    cents") because the abuse surface is unbounded — fixed 1¢ caps
    the drift to a single cent regardless of reserve size, with a
    per-policy override wired via `policies.consume_epsilon_cents` for
    the rare operator that needs it.

    The `ApproximateBudget` endpoint is advisory only — never feed a
    gate, rate-limit, or agent-side decision off it; an outage of all
    three sources returns 503, NOT `≈ $0 spent`. The reservation
    envelope TTL is 300s (or operator-configured); a `/track` arriving
    after TTL expiry returns `RESERVATION_NOT_FOUND` and the operator
    must retry with a fresh `/gate`. `consume_v3.lua`'s
    orphan-tolerance invariant (`pkey TTL'd → RESERVATION_NOT_FOUND`)
    treats a malformed reservation record as missing by design, since
    the cap check is reserved for the gate-bypass case only. Consume
    time can never revalidate the reserve's commitment against a new
    operator-tightened cap: the cap is fresh at `/track` (re-fetched
    in Rust) but the `authorized_cents` ceiling is sealed at `/gate`
    time. `ε > 5¢` produces a warning at startup (ADR-005) —
    operators that need wider tolerance should re-evaluate the reserve
    projection rather than raise ε.
