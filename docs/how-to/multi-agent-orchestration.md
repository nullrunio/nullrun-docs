---
title: Multi Agent Orchestration
description: Orchestrate sub-agents with shared kill semantics: a top-level trip propagates to every child through the control plane.
---

# Multi-agent orchestration

When one agent delegates to sub-agents — a LangGraph supervisor, a
CrewAI crew, an OpenAI Agents `Runner` with handoffs, or a custom
orchestrator — NullRun tracks each sub-agent independently under the
same workflow.

The rule is: **each `with workflow(...)` block creates its own
budget pool. Nesting does NOT inherit budget — the inner block has
its own pool.**

## LangGraph supervisor → sub-agents

```python title="langgraph_orchestrator.py"
from typing import TypedDict
from langgraph.graph import END, StateGraph
from langchain_openai import ChatOpenAI

import nullrun
from nullrun import init_or_die, protect, workflow, shutdown

init_or_die()
llm = ChatOpenAI(model="gpt-4o-mini")


class State(TypedDict):
    topic: str
    research: str
    draft: str


@protect
def research_node(state: State) -> State:
    """Sub-agent — its @protect is a gate for the LLM call only."""
    out = llm.invoke(f"Research {state['topic']}")
    return {"research": out.content}


@protect
def writer_node(state: State) -> State:
    out = llm.invoke(f"Write a draft using: {state['research']}")
    return {"draft": out.content}


def supervisor(state: State) -> str:
    return END  # or "research" / "writer"


with workflow("research-supervisor"):
    graph = StateGraph(State)
    graph.add_node("research", research_node)
    graph.add_node("writer", writer_node)
    graph.add_conditional_edges("supervisor", supervisor)
    graph.set_entry_point("supervisor")
    app = graph.compile()
    app.invoke({"topic": "LLM cost trends"})
```

Each `research_node` / `writer_node` is `@protect`-wrapped, so the
gate runs per node invocation, not per `app.invoke()` call.

`@protect` on each sub-agent ensures the gate runs before the LLM
call. The `with workflow("research-supervisor")` block scopes
budget attribution to the `research-supervisor` workflow — every
LLM call inside counts against that workflow's budget.

Nesting `with workflow("research-subagent")` inside does **not**
inherit the outer workflow's budget: each `workflow()` block creates
its own `workflow_id` with its own budget pool. To share a budget
across the whole orchestration tree, use ONE `workflow()` block
around the orchestrator (the pattern above). To give each sub-agent
an independent budget, use distinct workflow names — but they
become separate budget pools:

```python title="separate_workflows.py"
with workflow("research-supervisor"):
    with workflow("research-subagent") as research_wf:
        research_node(state)  # counts against research-subagent's budget
    with workflow("writer-subagent") as writer_wf:
        writer_node(state)    # counts against writer-subagent's budget
```

This is the **independent-pools** pattern — useful when sub-agents
have distinct budget allocations (e.g. one sub-agent handles paid
API calls, another is read-only), but you lose the "one cap protects
everything" guarantee.

Full LangGraph, CrewAI, and OpenAI Agents orchestration examples live
in [`nullrun-examples/examples/`](https://github.com/nullrunio/nullrun-examples/tree/master/examples)
— `langgraph_basic.py`, `crewai_basic.py`, and
`openai_agents_basic.py` show the independent-pools wiring.

## Operator kill across the tree

When an operator hits **Kill** in the dashboard, the WS push
delivers a `state_change(killed)` to **every** connected SDK client
holding the workflow's key. If multiple `@protect` calls are in-flight
across the orchestration tree, they all receive the kill signal at
their next yield boundary. See
[Control plane → kill contract](../concepts/control-plane.md#how-the-sdk-reacts)
for the wire-level details.

## Common pitfalls

| Pitfall | Symptom | Fix |
|---|---|---|
| Missing `with workflow(...)` around the orchestrator | Each sub-agent gets its own ad-hoc workflow_id, no shared budget pool across the tree | Wrap the whole tree in one workflow block |
| Each sub-agent has its own key | Sub-agents share nothing — kill signal only reaches the one bound to the killed workflow | Use one key for the orchestrator and let sub-agents inherit |
| Catching `Exception` instead of `BaseException` around the orchestration loop | Kill signal swallowed, agents keep running | Catch `WorkflowKilledInterrupt` explicitly first |

## See also

- [Workflow context](../concepts/workflow.md) — how `workflow()` scopes events
- [Chain context](../concepts/workflow.md#chain-context) — soft mode for multi-step orchestrations
- [Use with LangGraph](langgraph.md) — single-agent LangGraph example
- [Use with OpenAI Agents](openai-agents.md) — single-agent example
