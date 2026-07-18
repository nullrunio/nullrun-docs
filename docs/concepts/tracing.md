# Tracing

Every NullRun event carries a `trace_id` and a `span_id` so you can
correlate SDK-side calls with the gateway's audit log. Multi-agent
orchestrations additionally carry a `parent_trace_id` so the cost of
LLM calls inside a sub-agent rolls up to the orchestration row.

This page covers what the SDK writes, what the backend stores, and how
to query the unified view.

## The three identifiers

| Field | When written | Where it flows |
|---|---|---|
| `trace_id` | Created at SDK init (root) or when you call `with span(...)` for a nested span. Stays constant for the lifetime of a single workflow run. | Every `/gate`, `/track`, and `track_*` call |
| `span_id` | Created for each `@protect` invocation and each `with span(...)` block. New on every gate entry. | Decision log + cost_events |
| `parent_trace_id` | Set when a sub-agent runs under an orchestration root. The sub-agent's `trace_id` becomes its `parent_trace_id`. | Decision log (orchestration row only) |

## Single-agent trace

```python title="single_agent_trace.py"
import nullrun
from nullrun import init_or_die, protect, workflow, shutdown

init_or_die()
client = OpenAI()


@protect
def answer(prompt: str) -> str:
    return client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    ).choices[0].message.content


with workflow("customer-onboarding"):
    print(answer("What is LLM cost management?"))
```

The `with workflow("customer-onboarding")` block pins the
`workflow_id` for every `@protect` call inside. The SDK assigns a
fresh `trace_id` at `init()` time and reuses it across every
`/gate`, `/track`, and `track_*` call within the run. Each
`@protect` invocation creates a new `span_id`, so the audit log
shows distinct entries per call.

In the dashboard **Workflows → customer-onboarding → Decisions**:

```
trace_id    span_id       decision  reason            cost_cents
--------    --------      --------  ------            ----------
a1b2c3...   span-001      allow     —                 2.30
a1b2c3...   span-002      allow     —                 1.85
a1b2c3...   span-003      block     BUDGET_EXCEEDED   —
```

Three rows, one trace, three spans, one workflow.

## Multi-agent trace (parent / child)

When an orchestrator delegates to sub-agents, the SDK sets
`parent_trace_id` so the cost rolls up correctly:

```python title="multi_agent_trace.py"
from langgraph.graph import StateGraph
import nullrun
from nullrun import init_or_die, protect, workflow, span, shutdown

init_or_die()


@protect
def research_node(state): ...
@protect
def writer_node(state): ...


# Outer block pins the orchestration root.
with workflow("research-supervisor"):
    graph = StateGraph(...)
    graph.add_node("research", research_node)
    graph.add_node("writer", writer_node)
    app = graph.compile()
    app.invoke({"topic": "LLM cost trends"})


if __name__ == "__main__":
    try:
        with workflow("research-supervisor"):
            app.invoke({"topic": "LLM cost trends"})
    finally:
        shutdown()
```

If a sub-agent runs under its own `with workflow("research-subagent")`
context, the SDK captures the orchestration's `trace_id` as the
sub-agent's `parent_trace_id`. In the cost_events JOIN, the
orchestration row carries the rolled-up spend across every sub-agent
LLM call.

In the dashboard the orchestration view shows:

```
trace_id    parent_trace_id  workflow              span_id      cost_cents
--------    ---------------  --------              --------     ----------
root-001    —                research-supervisor   orchestration  8.40
root-001    sub-tr-002       research-subagent     span-007      3.10
root-001    sub-tr-003       writer-subagent       span-008      5.30
```

The orchestration row sums to `8.40` because it's the parent of the
two sub-agent spans.

## Manual spans with `with span(...)`

Use `with span(...)` when you want to group several `@protect` calls
under one logical operation:

```python title="span_grouping.py"
import nullrun
from nullrun import init_or_die, protect, span, shutdown

init_or_die()


@protect
def step_a(): ...
@protect
def step_b(): ...
@protect
def step_c(): ...


with span("phase-1"):
    step_a()  # span_id=phase-1
    step_b()  # still under phase-1
with span("phase-2"):
    step_c()  # new span_id=phase-2
```

Each `with span(...)` creates a new `span_id`. The `trace_id` stays
the same across both blocks (the workflow-level trace). Useful when
you want to filter the decision log by phase without needing separate
workflows.

## How the SDK handles nested context

The SDK uses Python `ContextVar`s for `trace_id`, `span_id`,
`workflow_id`, and `chain_id`. Token-based resets mean nested `with`
blocks restore the prior values on exit:

```python title="nested_context.py"
with workflow("outer"):
    # workflow_id = "outer"
    with workflow("inner"):
        # workflow_id = "inner"
        step()
    # workflow_id restored to "outer"
    step()
```

This works across threads inside the same process (each thread gets
its own contextvar copy) and across async tasks (each task inherits
the parent context).

## When to use which

| Pattern | Use when |
|---|---|
| `with workflow("name")` | One logical agent run (one cap, one kill target) |
| `with chain("id")` | Soft-mode gate for a multi-step loop inside one workflow |
| `with span("name")` | Group several calls under one trace without changing workflow boundaries |
| `with agent("id")` | Tag events with an agent identity distinct from the workflow (multi-tenant routing) |

## Querying the unified view

The cost_events table joins three ways depending on what you're
asking:

| Question | Query |
|---|---|
| What's the total spend per workflow this period? | `SELECT workflow_id, SUM(cost_cents) FROM cost_events WHERE period = ? GROUP BY workflow_id` |
| What did this agent run cost, including sub-agents? | `WHERE trace_id = ?` (the orchestration trace_id; sub-agent rows have it as `parent_trace_id`) |
| What's the slowest gate decision in this run? | `WHERE trace_id = ? ORDER BY lua_eval_ms DESC LIMIT 10` |
| How much did this particular tool call cost? | `WHERE span_id = ?` |

The `parent_trace_id` column is the join key for the orchestration
rollup. See [Reference → HTTP API → cost_events](../reference/http-api.md#sdk-endpoints)
for the full schema.

## See also

- [Workflow context](workflow.md) — workflow_id and chain_id
- [Span API in the SDK reference](../reference/sdk-api.md)
