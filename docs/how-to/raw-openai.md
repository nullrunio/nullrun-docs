# Raw `openai` SDK

If you use the `openai` package directly (no LangChain / LlamaIndex /
CrewAI on top), install the OpenAI extra:

```bash
pip install "nullrun[openai]"
```

```python
import nullrun
from openai import OpenAI

nullrun.init(api_key="nr_live_...")
client = OpenAI()
resp = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Hello"}],
)
```

Patched via the `httpx` transport hook in `nullrun.instrumentation.auto`
— the OpenAI SDK uses `httpx` under the hood, so the SDK reads the
response body, extracts `usage.prompt_tokens` /
`usage.completion_tokens`, and emits a `track_llm` event.

> `nullrun[openai]` is for the **raw** `openai` SDK — it is **not**
> the OpenAI Agents SDK. For agents use [`nullrun[agents]`](openai-agents.md).

## See also

- [Auto-instrumentation overview](auto-instrumented-frameworks.md)
- [Use with OpenAI Agents](openai-agents.md)
- [Quickstart](../getting-started/quickstart.md)