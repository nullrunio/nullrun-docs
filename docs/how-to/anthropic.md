# Anthropic

Install:

```bash title="shell"
pip install "nullrun[anthropic]"
```

```python title="anthropic_client.py"
import nullrun
from anthropic import Anthropic

nullrun.init(api_key="nr_live_...")

client = Anthropic()
resp = client.messages.create(
    model="claude-3-5-sonnet-latest",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello"}],
)
```

Patched via the `httpx` transport hook in
`nullrun.instrumentation.auto` — see the
[auto-instrumentation overview](auto-instrumented-frameworks.md#how-the-httpx-transport-hook-works)
for how the hook reads the response body, extracts
`usage.input_tokens` / `usage.output_tokens`, and emits a `track_llm`
event.

## See also

- [Auto-instrumentation overview](auto-instrumented-frameworks.md)
- [Quickstart](../getting-started/quickstart.md)
- [Track or cap spend](../concepts/budgets.md)
