---
title: LangGraph agent
description: Gate and cost-track a LangGraph agent with @protect, and fall back to an entry-point wrapper when the auto-patch misses your graph.
maturity: stable
---

# Protect a LangGraph agent

The SDK attaches to LangGraph on its own. The attachment is installed
once per process — see [LLM frameworks](llm-frameworks.md) for the
rule.

Import LangGraph before that happens. The patch wraps the `Pregel`
class, so a module that arrives after the attachment is never patched.

No vendor extra is needed. Install LangGraph and whatever chat model
client you use next to the SDK.

```bash title="shell"
pip install nullrun langgraph langchain-openai
```

## The wiring

```python title="langgraph_agent.py"
from langchain_openai import ChatOpenAI
from langgraph.graph import END, MessagesState, StateGraph

from nullrun import protect

llm = ChatOpenAI(model="gpt-4o-mini")


@protect
def chat(state: MessagesState):
    return {"messages": [llm.invoke(state["messages"])]}


graph = StateGraph(MessagesState)
graph.add_node("chat", chat)
graph.add_edge("chat", END)
graph.set_entry_point("chat")
app = graph.compile()

result = app.invoke({"messages": [{"role": "user", "content": "Hi"}]})
```

Every model call in the graph is cost-attributed to the workflow. The
`@protect` wrapper on the node is the gate boundary: the gateway
decides before the node body runs.

## When the automatic attachment misses the graph

Two cases need a different wiring:

- the graph is compiled in a worker thread, or
- LangGraph is imported after `init()` or after the first `@protect`
  call has already run.

Wrap the entry point instead of the graph. Every invocation passes
through that function, so the gate fires once per run:

```python title="langgraph_entrypoint.py"
from langchain_openai import ChatOpenAI
from langgraph.graph import END, MessagesState, StateGraph

from nullrun import protect

llm = ChatOpenAI(model="gpt-4o-mini")


def chat(state: MessagesState):
    return {"messages": [llm.invoke(state["messages"])]}


graph = StateGraph(MessagesState)
graph.add_node("chat", chat)
graph.add_edge("chat", END)
graph.set_entry_point("chat")
app = graph.compile()


@protect
def run_agent(prompt: str) -> str:
    result = app.invoke({"messages": [{"role": "user", "content": prompt}]})
    return result["messages"][-1].content
```

This also keeps `app` a plain compiled graph, so an `isinstance` check
against the graph class in your own code keeps working.

## See also

- [Quickstart](../getting-started/quickstart.md)
- [LLM frameworks](llm-frameworks.md) — the other supported frameworks
- [Examples → LangGraph](https://github.com/nullrunio/nullrun-examples/blob/master/examples/langgraph_basic.py)
