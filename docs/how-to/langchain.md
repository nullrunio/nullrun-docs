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

## Test coverage

Per NullRun's testing policy (see the SDK README), LangChain
callback patching exists but **has no dedicated callback-integration
test**. The `patch_langchain_callback` hook is exercised by the
unified-fingerprint test (`tests/test_unified_fingerprint.py`),
which validates the fingerprint shape but not the callback's wire
effect. This is documented per §8 of the source-of-truth
positioning — verify behaviour against your real workload before
relying on the callback path.