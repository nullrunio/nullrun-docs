---
title: Multi-agent orchestration
description: Delegate from one orchestrator to sub-agents inside one process, and share one budget pool and one kill signal across the whole tree.
maturity: stable
---

# Multi-agent orchestration

An orchestrator delegates to sub-agents: a LangGraph supervisor, a
CrewAI crew, an OpenAI Agents runner with handoffs, or a hand-written
loop.

This page covers sub-agents inside **one process**. For running
separate workflows on separate keys, see
[Run several agents on one host](multi-agent.md).

## One workflow block for the whole tree

Wrap the orchestrator in a single `workflow()` block. The block gives
every call inside it the same trace.

```python title="langgraph_orchestrator.py"
from typing import TypedDict

from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from nullrun import protect, workflow

llm = ChatOpenAI(model="gpt-4o-mini")


class State(TypedDict):
    topic: str
    research: str
    draft: str


@protect
def research_node(state: State) -> State:
    out = llm.invoke(f"Research {state['topic']}")
    return {"research": out.content}


@protect
def writer_node(state: State) -> State:
    out = llm.invoke(f"Write a draft using: {state['research']}")
    return {"draft": out.content}


with workflow("research-supervisor"):
    graph = StateGraph(State)
    graph.add_node("research", research_node)
    graph.add_node("writer", writer_node)
    graph.add_edge("research", "writer")
    graph.add_edge("writer", END)
    graph.set_entry_point("research")
    app = graph.compile()
    app.invoke({"topic": "LLM cost trends"})
```

The gate runs per node, because each node is `@protect`-wrapped. One
wrapper around `app.invoke()` would gate the whole graph once.

## The budget comes from the API key

The cap is always the budget of the workflow the API key is bound to.
The gateway derives that binding from the key. It does not take the
workflow name from the SDK.

So a `workflow()` block does not open a second budget pool. It scopes
the labels on the events emitted inside it.

Use one `workflow()` block per process. If you want a separate budget
per sub-agent, give each sub-agent its own API key and its own
process.

## Naming the sub-agents

`agent()` and `span()` label the work inside the tree without opening a
new budget.

```python title="labelled_subagents.py"
from typing import TypedDict

from langchain_openai import ChatOpenAI

from nullrun import agent, protect, span

llm = ChatOpenAI(model="gpt-4o-mini")


class State(TypedDict):
    topic: str
    research: str


@protect
def research_node(state: State) -> State:
    with agent("researcher"):
        with span("search"):
            out = llm.invoke(f"Research {state['topic']}")
    return {"research": out.content}
```

## Kill reaches the whole tree

An operator hits **Kill** in the control center. The control plane pushes the
new state to every SDK client in the organization. A client raises at
its next protected call on the killed workflow.

The exception depends on the function type. A sync function raises
`NullRunBlockedException` with `error_code` `NR-W002`. A coroutine
raises `WorkflowKilledInterrupt`. The async wrapper leaves the original
exception alone so an async framework can cancel the task on the type
it expects. See
[Control plane → Sync and async behave differently](../concepts/control-plane.md#sync-and-async-behave-differently)
for the full matrix.

Catch the kill by name and re-raise it:

```python title="kill_handling.py"
from nullrun import WorkflowKilledInterrupt


async def run_orchestration() -> None:
    try:
        await agent_step("do something")
    except WorkflowKilledInterrupt:
        # The operator killed the workflow. Stop the tree and re-raise.
        raise


async def agent_step(prompt: str) -> None:
    """Your agent work goes here."""
```

## Common pitfalls

| Pitfall | Symptom | Fix |
|---|---|---|
| No `workflow()` block around the orchestrator | Every protected call is its own trace | Wrap the tree in one block |
| A nested `workflow()` per sub-agent | Each block relabels the events inside it | Use `agent()` and `span()` for labels |
| One key per sub-agent | Every sub-agent needs its own process and its own key | Use one key for the orchestrator |
| A broad `except Exception` that does not re-raise | The kill is swallowed and the agent keeps running | Catch `WorkflowKilledInterrupt` first |

## See also

- [Run several agents on one host](multi-agent.md) — separate processes
  and separate keys
- [Workflow context](../concepts/workflow.md) — what `workflow()` scopes
- [Chain context](../concepts/workflow.md#chain-context) — soft mode for
  multi-step orchestrations
- [Use with LangGraph](langgraph.md) — the single-agent wiring
