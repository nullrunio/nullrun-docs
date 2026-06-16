# Budgets

A budget is a hard cap on cost for a single workflow run. When the
budget is exceeded, the workflow is halted and the agent stops.

## How budgets are enforced

Two gates work together:

1. **Pre-flight `/check`** — on every `@protect`-wrapped call, the SDK
   asks the gateway "is there any budget left?" with `tokens=1`. If the
   workflow has already exceeded its budget, the call is rejected
   *before* it runs.

2. **`/track` after the fact** — when the call completes, the SDK
   reports the actual cost. The gateway updates the cumulative spend
   and may reject subsequent calls.

The pre-flight is binary (any budget left, yes/no). The post-flight
is the source of truth for cumulative spend.

## Set a budget

In the NullRun dashboard, open a workflow and set the per-workflow
budget. Or via the API:

```bash
curl -X PUT https://api.nullrun.io/api/v1/workflows/$WORKFLOW_ID \
  -H "Authorization: Bearer $NULLRUN_API_KEY" \
  -d '{"budget_cents": 500}'
```

Once set, any call inside `@protect(workflow_id="$WORKFLOW_ID")` will
stop the moment cumulative cost exceeds 500¢.

## See also

- [Circuit breaker](circuit-breaker.md)
- [How-to → Set a hard cost cap](../how-to/cost-cap.md)
