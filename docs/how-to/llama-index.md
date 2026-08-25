# LlamaIndex

Install:

```bash title="shell"
pip install "nullrun[llama-index]"
```

```python title="llama_index_chat.py"
import nullrun
from llama_index.core.llms import ChatMessage
from llama_index.llms.openai import OpenAI

nullrun.init(api_key="nr_live_...")

llm = OpenAI(model="gpt-4o-mini")
resp = llm.chat([ChatMessage(role="user", content="Hello")])
```

Patched via `nullrun.instrumentation.llama_index.patch_llama_index`,
which monkey-patches the LLM class to wrap each `chat` / `complete`
call so the SDK sees the raw usage.

## See also

- [Auto-instrumentation overview](auto-instrumented-frameworks.md)
- [Quickstart](../getting-started/quickstart.md)
