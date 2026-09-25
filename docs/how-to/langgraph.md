---
title: Langgraph
description: Auto-instrument a LangGraph agent with @protect, or wrap nodes manually when you need fine-grained control over the gate decision.
---

# Protect a LangGraph agent

The SDK auto-patches LangGraph on the **first `@protect` call** —
no manual wrapper needed for the common case.

```bash title="shell"
pip install nullrun langgraph langchain-openai
```

```python title="langgraph_agent.py"
from langchain_openai import ChatOpenAI
from langgraph.graph import END, MessagesState, StateGraph

from nullrun import protect

# The runtime + LangGraph Pregel hook are attached lazily on
# the first @protect call.
llm = ChatOpenAI(model="gpt-4o-mini")

@protect
def chat(state: MessagesState):
    return {"messages": [llm.invoke(state["messages"])]}

# `StateGraph(MessagesState)` replaces the deprecated
# `langgraph.graph.MessageGraph` (removed in langgraph 1.0).
graph = StateGraph(MessagesState)
graph.add_node("chat", chat)
graph.add_edge("chat", END)
graph.set_entry_point("chat")
app = graph.compile()

result = app.invoke({"messages": [{"role": "user", "content": "Hi"}]})
```

Every LLM call inside the graph is now cost-attributed and gated by
your workspace policy. The same auto-instrumentation path works for
any LangChain `Runnable` and most LangGraph node types.

## Manual wrapper

If you need to attach the callback manually — e.g. inside a library
that re-compiles graphs after the runtime was created — the explicit
form is:

```python title="langgraph_manual_wrapper.py"
from nullrun.instrumentation.auto import patch_langgraph_compiled

patch_langgraph_compiled()  # idempotent — safe to call repeatedly
app = graph.compile()
```

`patch_langgraph_compiled` wraps every compiled app's `.invoke` and
`.stream` methods to inject the NullRun callback into the LangChain
`config["callbacks"]` list per call. The control-plane kill/pause
subscription is **independent** — it starts on the first `@protect`
call and works for every protected call in the process regardless of
whether you used the manual patch or the auto-instrumentation path.

## See also

- [Quickstart](../getting-started/quickstart.md)
- [Examples → LangGraph](https://github.com/nullrunio/nullrun-examples/blob/master/examples/langgraph_basic.py)
