# Set a hard cost cap

A cost cap is the simplest way to make sure an agent can't blow past
your budget. It works at two levels:

1. **Per-workflow** — set on a workflow, halts the run when cumulative
   cost exceeds the cap.
2. **Per-call** — set on a `@protect` call, rejects any single call that
   would exceed the cap.

## Per-workflow

In the dashboard, open the workflow and set the budget. Or via the
HTTP API:

```bash
curl -X PUT https://api.nullrun.io/api/v1/workflows/$WORKFLOW_ID \
  -H "Authorization: Bearer $NULLRUN_API_KEY" \
  -d '{"budget_cents": 500}'
```

Then in the SDK:

```python
@protect(workflow_id="my-workflow")
def run(): ...
```

Cumulative cost > 500¢ → `BudgetExceededError` on the next call.

## Per-call

```python
@protect(per_call_cost_cents=10)
def cheap_step(): ...
```

A single call projected to cost > 10¢ → rejected.

## See also

- [Budgets](../concepts/budgets.md)
- [Examples → cost cap demo](https://github.com/nullrunio/nullrun-examples/blob/main/examples/cost_cap_demo.py)
