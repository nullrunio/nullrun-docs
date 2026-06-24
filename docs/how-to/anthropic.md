# Anthropic

Install:

```bash
pip install "nullrun[anthropic]"
```

```python
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

Patched via the `httpx` transport hook in `nullrun.instrumentation.auto`
— the Anthropic SDK uses `httpx` under the hood, so the SDK reads
the response body, extracts `usage.input_tokens` /
`usage.output_tokens`, and emits a `track_llm` event with the
extracted tokens. Cost is recomputed on the backend from the org's
pricing policy.

## See also

- [Auto-instrumentation overview](auto-instrumented-frameworks.md)
- [Quickstart](../getting-started/quickstart.md)
- [Track or cap spend](../concepts/budgets.md)