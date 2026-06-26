# AutoGen

Install:

```bash title="shell"
pip install "nullrun[autogen]"
```

```python title="autogen_assistant.py"
import nullrun
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient

nullrun.init(api_key="nr_live_...")

model = OpenAIChatCompletionClient(model="gpt-4o-mini")
assistant = AssistantAgent("assistant", model_client=model)
result = await assistant.run(task="Hello")
```

Patched via `nullrun.instrumentation.autogen.patch_autogen`, which
hooks the AutoGen model-client path so every agent run emits a
`track_llm` event. The vendor imports (`autogen-agentchat`,
`autogen-ext[openai]`) are wrapped in `try/except ImportError`, so
installing only this extra group does not crash on `init()`.

## See also

- [Auto-instrumentation overview](auto-instrumented-frameworks.md)
- [Quickstart](../getting-started/quickstart.md)