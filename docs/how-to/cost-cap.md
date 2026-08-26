---
title: Cost Cap
description: Set a per-workflow hard cost cap with alert thresholds, and use Soft mode with an active chain to allow a controlled overdraft.
---

# Set a hard cost cap

A cost cap is the simplest way to make sure an agent can't blow past
your budget. It works at two levels:

1. **Per-workflow** — set on a workflow, halts the run when cumulative
   cost exceeds the cap.
2. **Per-call** — projected cost from the SDK, rejects any single call
   that would exceed the cap.

## Per-workflow

In the dashboard, open the workflow and set the budget. Or via the
HTTP API:

```bash title="set_budget.sh"
curl -X PATCH https://api.nullrun.io/api/v1/orgs/$ORG_ID/workflows/$WORKFLOW_ID \
  -H "X-API-Key: *** \
  -H "X-Signature: $(compute_hmac)" \
  -H "X-Signature-Timestamp: $(date +%s)" \
  -H "Content-Type: application/json" \
  -d '{"budget_cents": 500}'
```

> Auth uses `X-API-Key` plus an HMAC-SHA256 signature over
> `timestamp:api_key:body_hash` (see the
> [HTTP API reference](../reference/http-api.md#authentication))
> and the SDK's `NULLRUN_SECRET_KEY`. Bearer session tokens are for
> dashboard / admin endpoints only.

Then in the SDK:

```python title="budgeted_run.py"
import nullrun
from nullrun import init, protect

init(api_key="nr_live_...")

with nullrun.workflow("my-workflow"):
    @protect
    def run(): ...
```

Cumulative cost > 500¢ → `NullRunBudgetError` raised on the next
gate call with `error_code = "NR-B004"` (wire `BUDGET_HARD_BLOCKED`).
For non-budget policy blocks (tool block, sensitive tool) the generic
`NullRunBlockedException` is raised with
`error_code = "NR-T001"` (wire `TOOL_BLOCKED`).
See [Errors](../reference/errors.md) for the full catalog and the
recommended `except` pattern.

`max_budget_cents == 0` means **"no per-key budget configured"**, not
"block everything" — the gate passes through to the org-level plan
cap. See [Budgets → How to set the budget](../concepts/budgets.md#how-to-set-the-budget).

## Per-call

The SDK does not project per-call cost on its own — the per-call
cap is enforced by the workspace policy on the gateway. When the
policy carries a per-call threshold, the `/gate` call rejects any
single call whose projected cost would exceed the cap *before* the
model is invoked. The SDK raises `NullRunBlockedException` with
`error_code = "NR-B004"` (wire `BUDGET_HARD_BLOCKED`).

If you need to skip pre-flight in tests, use a workflow with a low
budget instead.

## See also

- [Budgets](../concepts/budgets.md) — reservation lifecycle and the
  pre-flight `/gate` end-to-end
- [Errors](../reference/errors.md)
- [Examples → cost cap demo](https://github.com/nullrunio/nullrun-examples/blob/main/examples/cost_cap_demo.py)
