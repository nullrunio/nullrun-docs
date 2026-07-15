# Workflow context

A **workflow** is a single agent run. It has a unique `workflow_id`
that groups all its calls together for cost attribution, policy
enforcement, and audit.

## Default vs explicit

A **workflow_id** is **not** auto-generated per `@protect` invocation.
Instead, since Phase 139 every API key is minted bound to exactly one
workflow, and the SDK reads that binding during `init()`. The SDK does
not invent workflow IDs — if you want a different grouping than the
API key's binding, scope the work inside a `nullrun.workflow(...)`
context. **`@protect` itself takes no kwargs**:

```python title="workflow_scoped_agent.py"
import nullrun
from nullrun import init, protect

init(api_key="nr_live_...")

with nullrun.workflow("user-123:research-task-456"):
    @protect
    def research(question: str) -> str: ...
```

Every call inside `research()` shares the same workflow and can be
addressed as one unit in the dashboard. The explicit
`workflow("user-123:research-task-456")` contextvar wins over the
API key's binding for the duration of the block.

Legacy keys minted before Phase 139 carry no `workflow_id` binding —
for those, the SDK emits a one-time warning at startup and the
control plane cannot honour KILL/PAUSE for that workflow. Rotate
the key in the dashboard to enable control-plane enforcement.

## What the workflow ID does

- Aggregates cost per workflow
- Carries the policy (budget, allowed tools, sensitive tools, etc.)
- Anchors the [control plane](control-plane.md) (kill / pause
  broadcasts to all `@protect` calls with the same `workflow_id`)
- Powers the audit log
- Carries `trace_id` + `parent_trace_id` for multi-agent span
  attachment (since SDK 0.13.6 — see
  [parent_trace_id cost_events column](../reference/http-api.md#sdk-endpoints)).
  When an LLM call sits inside a `with chain(...)` block or a
  LangGraph sub-agent, the SDK attaches the chain's trace_id as
  `parent_trace_id` so the unified cost_events SELECT third JOIN
  arm surfaces the LLM cost on the orchestration row.

## Chain context (soft-mode budget gate)

A **chain** groups consecutive `@protect` calls under a single
budget reservation. Use it when a single user request fans out
into a multi-step agent loop and you want one budget decision
across the whole loop instead of one decision per step:

```python title="chain_example.py"
import nullrun
from nullrun import init, protect

init(api_key="nr_live_...")

with nullrun.workflow("research-task"):
    with nullrun.chain("loop-1"):
        @protect
        def step1(): ...
        @protect
        def step2(): ...
        @protect
        def step3(): ...
```

The SDK's in-process gate cache collapses same-key
`(workflow_id, chain_id, model)` calls to a single `/gate`
round-trip with a 5s TTL — see
[Budgets → v3 protocol negotiation](budgets.md#v3-protocol-negotiation)
and the `NULLRUN_GATE_CACHE_DISABLE=1` opt-out in
[Configuration](../getting-started/configuration.md).

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
called), the gateway broadcasts a `state_change` over
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
