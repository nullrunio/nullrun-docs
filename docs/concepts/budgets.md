# Budgets

A budget is a hard cap on cost for a single workflow run. When the
budget is exceeded, the workflow is halted and the agent stops.

## How budgets are enforced

Three endpoints work together:

1. **Pre-flight `/api/v1/gate`** — on every `@protect`-wrapped call,
   the SDK asks the gateway "is there any budget left?" with `tokens=1`.
   This is a **binary** pre-flight, not a cost prediction. If the
   workflow has already exceeded its budget, the call is rejected
   *before* it runs. (The legacy `/api/v1/check` endpoint still
   exists for backward compatibility — new code uses `/gate` per
   `Transport.check()` in `src/nullrun/transport.py`.)

2. **Reservation `/api/v1/execute`** — synchronously evaluates the
   gate (budget + policy + sensitive tool rules) and **reserves** the
   projected cost. Returns a reservation token. If the budget can't
   accommodate the projected cost, the gateway returns
   `validation_error` / `plan_limit_exceeded` (HTTP 422) and the SDK
   raises `NullRunBlockedException` (or `NullRunBudgetError` for the
   budget case). The call is blocked before it runs.

3. **`/api/v1/track` after the fact** — when the call completes, the
   SDK reports the actual cost. The gateway either **commits** the
   reservation (real cost was ≤ projected) or **releases** it (real
   cost was lower). Cumulative spend is updated from committed
   reservations + tracked cost.

The pre-flight is binary (any budget left, yes/no). The reservation
is the source of truth for cumulative committed spend. The
post-flight `/track` reconciles any drift.

## Set a budget

In the NullRun dashboard, open a workflow and set the per-workflow
budget. Or via the API:

```bash
curl -X PATCH https://api.nullrun.io/api/v1/orgs/$ORG_ID/workflows/$WORKFLOW_ID \
  -H "X-API-Key: $NULLRUN_API_KEY" \
  -H "X-Signature: $(compute_hmac)" \
  -H "X-Signature-Timestamp: $(date +%s)" \
  -H "Content-Type: application/json" \
  -d '{"budget_cents": 500}'
```

Inside `@protect`, set the workflow id via `nullrun.workflow(...)`
(the decorator itself takes no kwargs):

```python
import nullrun
from nullrun import init, protect

init(api_key="nr_live_...")

with nullrun.workflow("my-workflow"):
    @protect
    def step(): ...
```

Once set, any call inside that workflow context stops the moment
cumulative committed cost exceeds 500¢.

## See also

- [Circuit breaker](circuit-breaker.md)
- [How-to → Set a hard cost cap](../how-to/cost-cap.md)
- [Errors](../reference/errors.md)
