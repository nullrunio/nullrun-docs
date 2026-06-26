# LangChain

Install:

```bash title="shell"
pip install "nullrun[langchain]"
```

```python title="langchain_chat.py"
import nullrun
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

nullrun.init(api_key="nr_live_...")

llm = ChatOpenAI(model="gpt-4o-mini")
resp = llm.invoke([HumanMessage(content="Hello")])
```

`nullrun.init()` patches `BaseCallbackManager.__init__` via
`patch_langchain_callback` in `nullrun.instrumentation.auto`, so a
`NullRunCallback` is added to every `CallbackManager` on construction.
That callback fires the same `track_llm` path the httpx hook uses,
so cost tracking works for in-memory mock providers and callback-only
flows that don't hit the network (the httpx hook alone only covers
networking calls).

The same auto-instrumentation path works for any LangChain
`Runnable` — chains, agents, retrievers. For LangGraph specifically,
see [Protect a LangGraph agent](langgraph.md) — `Pregel.invoke` /
`Pregel.stream` get an extra wrapper layer via
`patch_langgraph_compiled`.

## See also

- [Auto-instrumentation overview](auto-instrumented-frameworks.md)
- [Protect a LangGraph agent](langgraph.md)
- [Quickstart](../getting-started/quickstart.md)