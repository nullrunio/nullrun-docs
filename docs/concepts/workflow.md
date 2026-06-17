# Workflow context

A **workflow** is a single agent run. It has a unique `workflow_id`
that groups all its calls together for cost attribution, policy
enforcement, and audit.

## Default vs explicit

By default, the SDK uses an auto-generated workflow ID per `@protect`
invocation. To attach a policy, budget, or run-time grouping, scope the
work inside a `nullrun.workflow(...)` context — **`@protect` itself
takes no kwargs**:

```python
import nullrun
from nullrun import init, protect

init(api_key="nr_live_...")

with nullrun.workflow("user-123:research-task-456"):
    @protect
    def research(question: str) -> str: ...
```

Every call inside `research()` shares the same workflow and can be
addressed as one unit in the dashboard.

## What the workflow ID does

- Aggregates cost per workflow
- Carries the policy (budget, allowed tools, sensitive tools, etc.)
- Anchors the [control plane](control-plane.md) (kill / pause
  broadcasts to all `@protect` calls with the same `workflow_id`)
- Powers the audit log

## How the workflow ends

A workflow is considered ended when:

- The wrapped function returns normally
- An exception propagates out of the wrapped function
- The workflow is killed or paused via the control plane (see
  [Control plane](control-plane.md))

If the SDK cannot reach the gateway to send a final state, it buffers
the event and retries on the next call.

## How kill / pause arrives

When an operator hits **Kill** in the dashboard (or the kill API is
called), the gateway broadcasts a `StateChange` over
`WS /ws/control/{org_id}`. The SDK receives it and:

| Situation | Result |
| --- | --- |
| A call is mid-execution | The interrupt is queued and raised at the next yield point as `WorkflowKilledInterrupt` (BaseException — see the kill contract) |
| A call has not started | The next `@protect` call raises `WorkflowKilledInterrupt` before the wrapped function runs |
| The WebSocket is down | The next `@protect` call does a synchronous `check_control_plane` poll and learns about the kill from `/api/v1/orgs/{org_id}/status` |

A pause lands the same way but raises `WorkflowPausedException`
(regular `Exception` subclass). Resume via the dashboard or the
`POST /api/v1/orgs/{org_id}/workflows/{workflow_id}/resume` endpoint.

## See also

- [Circuit breaker](circuit-breaker.md)
- [Control plane](control-plane.md)
- [Budgets](budgets.md)
