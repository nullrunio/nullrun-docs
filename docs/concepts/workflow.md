# Workflow context

A **workflow** is a single agent run. It has a unique `workflow_id`
that groups all its calls together for cost attribution, policy
enforcement, and audit.

## Default vs explicit

By default, the SDK uses an auto-generated workflow ID per `@protect`
invocation. To attach a policy, budget, or run-time grouping, pass
`workflow_id` explicitly:

```python
@protect(workflow_id="user-123:research-task-456")
def research(question: str) -> str: ...
```

Now every call inside `research()` shares the same workflow and can be
addressed as one unit in the dashboard.

## What the workflow ID does

- Aggregates cost per workflow
- Carries the policy (budget, allowed tools, sensitive tools, etc.)
- Anchors the control plane (kill / pause broadcasts to all
  `@protect` calls with the same `workflow_id`)
- Powers the audit log

## When the workflow ends

A workflow is considered ended when:

- The wrapped function returns normally
- An exception propagates out of the wrapped function
- The workflow is killed or paused via the control plane (see
  [Workflow killed / paused](circuit-breaker.md))

If the SDK cannot reach the gateway to send a final state, it buffers
the event and retries on the next call.

## See also

- [Circuit breaker](circuit-breaker.md)
- [Budgets](budgets.md)
