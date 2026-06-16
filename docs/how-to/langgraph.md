# Protect a LangGraph agent

Install with the LangGraph extra:

```bash
pip install "nullrun[langgraph]" langgraph langchain-openai
```

Wire `NullRunCallback` into your graph:

```python
from langchain_openai import ChatOpenAI
from langgraph.graph import END, MessageGraph

from nullrun import init
from nullrun.instrumentation.langgraph import NullRunCallback

init(api_key="nr_live_...")

llm = ChatOpenAI(model="gpt-4o-mini")

def chat(state):
    return {"messages": [llm.invoke(state["messages"])]}

graph = MessageGraph()
graph.add_node("chat", chat)
graph.add_edge("chat", END)
graph.set_entry_point("chat")
app = graph.compile()

result = app.invoke(
    [{"role": "user", "content": "Hi"}],
    config={"callbacks": [NullRunCallback()]},
)
```

Every LLM call inside the graph is now tracked, cost-attributed, and
gated by your workspace policy. The same callback works for any
LangChain `Runnable` and most LangGraph node types.

## See also

- [Quickstart](../getting-started/quickstart.md)
- [Examples → LangGraph](https://github.com/nullrunio/nullrun-examples/blob/main/examples/langgraph_basic.py)
