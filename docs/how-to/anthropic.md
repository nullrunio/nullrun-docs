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

Patched via the `httpx` transport hook in `nullrun.instrumentation.auto`
— the Anthropic SDK uses `httpx` under the hood, so the SDK reads
the response body, extracts `usage.input_tokens` /
`usage.output_tokens`, and emits a `track_llm` event with the
extracted tokens. Cost is recomputed on the backend from the org's
pricing policy.

## Test coverage

Per NullRun's testing policy (see the SDK README), transport patches
have dedicated end-to-end HTTP tests for **OpenAI** only. Anthropic
patches have extractor support but no dedicated end-to-end transport
test. Cost tracking therefore flows through the same code path as
the OpenAI patch — same `track_llm` event shape, same aggregator,
same `cost_events` row — but is not exercised by a per-vendor
integration test in this repo.

## See also

- [Auto-instrumentation overview](auto-instrumented-frameworks.md)
- [Quickstart](../getting-started/quickstart.md)
- [Track or cap spend](../concepts/budgets.md)