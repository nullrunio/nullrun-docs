---
title: Multi-agent orchestration
description: Delegate from one orchestrator to sub-agents inside one process, and share one budget pool and one kill signal across the tree.
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

Wrap the orchestrator in a single `workflow()` block. Every call inside
it lands on the same workflow.

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


def supervisor(state: State) -> str:
    return END


with workflow("research-supervisor"):
    graph = StateGraph(State)
    graph.add_node("research", research_node)
    graph.add_node("writer", writer_node)
    graph.add_conditional_edges("supervisor", supervisor)
    graph.set_entry_point("supervisor")
    app = graph.compile()
    app.invoke({"topic": "LLM cost trends"})
```

The gate runs per node, because each node is `@protect`-wrapped. One
wrapper around `app.invoke()` would gate the whole graph once.

## The budget comes from the API key

The cap is always the budget of the workflow the API key is bound to.
The gateway derives that binding from the key. It does not read the
workflow name from the SDK.

So a nested `workflow()` block does not open a second budget pool. It
does change the label on the events emitted inside it, which splits the
attribution across two names while the cap stays where the key put it.

Use one `workflow()` block per process. If you want a separate budget
per sub-agent, give each sub-agent its own API key and its own
process.

## Naming the sub-agents

`agent()` and `span()` label the work inside the tree without opening a
new budget.

```python title="labelled_subagents.py"
from nullrun import agent, span


@protect
def research_node(state: State) -> State:
    with agent("researcher"):
        with span("search"):
            out = llm.invoke(f"Research {state['topic']}")
    return {"research": out.content}
```

## Kill reaches the whole tree

An operator hits **Kill** in the dashboard. The control-plane push
carries the new state to every SDK client that holds the workflow's
key. Each client raises at its next protected call.

| Protected function | What propagates |
|---|---|
| Sync | `NullRunBlockedException` with `error_code` `NR-W002` |
| Async | `WorkflowKilledInterrupt` |

The async wrapper leaves the original exception alone so an async
framework can cancel the task on the type it expects. Catch it by name
in both cases:

```python title="kill_handling.py"
from nullrun import WorkflowKilledInterrupt, NullRunBlockedException


try:
    run_orchestration()
except WorkflowKilledInterrupt:
    raise
except NullRunBlockedException as exc:
    if exc.error_code == "NR-W002":
        raise
    raise
```

See [Control plane → What the agent sees](../concepts/control-plane.md#what-the-agent-sees)
for the full signal matrix.

## Common pitfalls

| Pitfall | Symptom | Fix |
|---|---|---|
| No `workflow()` block around the orchestrator | Events carry an ad-hoc workflow name | Wrap the tree in one block |
| A nested `workflow()` per sub-agent | Spend is split across names while one cap applies | Use `agent()` and `span()` for labels |
| One key per sub-agent | Every sub-agent needs its own process and its own key | Use one key for the orchestrator |
| Only `except Exception` around the loop | The kill is swallowed and the agent keeps running | Catch `WorkflowKilledInterrupt` first |

## See also

- [Run several agents on one host](multi-agent.md) — separate processes
  and separate keys
- [Workflow context](../concepts/workflow.md) — what `workflow()` scopes
- [Chain context](../concepts/workflow.md#chain-context) — soft mode for
  multi-step orchestrations
- [Use with LangGraph](langgraph.md) — the single-agent wiring
