# Protect a LangGraph agent

Install with the LangGraph extra:

```bash
pip install "nullrun[langgraph]" langgraph langchain-openai
```

`nullrun.init()` auto-instruments LangGraph — it attaches
`NullRunCallback` to any compiled graph once `init()` runs. **No
manual callback wiring needed** (the old
`from nullrun.instrumentation.langgraph import NullRunCallback`
import still works but is discouraged).

```python
from langchain_openai import ChatOpenAI
from langgraph.graph import END, MessagesState, StateGraph

from nullrun import init

init(api_key="nr_live_...")

llm = ChatOpenAI(model="gpt-4o-mini")

def chat(state: MessagesState):
    return {"messages": [llm.invoke(state["messages"])]}

# `StateGraph(MessagesState)` replaces the deprecated
# `langgraph.graph.MessageGraph` (removed in langgraph 1.0).
graph = StateGraph(MessagesState)
graph.add_node("chat", chat)
graph.add_edge("chat", END)
graph.set_entry_point("chat")
app = graph.compile()

result = app.invoke([{"role": "user", "content": "Hi"}])
```

Every LLM call inside the graph is now cost-attributed and gated by
your workspace policy. The same auto-instrumentation path works for
any LangChain `Runnable` and most LangGraph node types.

## Manual wrapper (advanced)

If you need to attach the callback manually — e.g. inside a library
that re-compiles graphs after `init()` ran — the canonical wrapper is:

```python
from nullrun.toolbox.langgraph import wrapper

app = wrapper(graph.compile())
```

This is preferred over `NullRunCallback()` because it also wires the
control-plane kill/pause subscription for the wrapped graph.

## See also

- [Quickstart](../getting-started/quickstart.md)
- [Examples → LangGraph](https://github.com/nullrunio/nullrun-examples/blob/main/examples/langgraph_basic.py)
