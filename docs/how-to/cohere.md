# Cohere

Install:

```bash
pip install "nullrun[cohere]"
```

```python
import nullrun
import cohere

nullrun.init(api_key="nr_live_...")

client = cohere.Client()
resp = client.chat(
    model="command-r-plus",
    message="Hello",
)
```

Patched via the per-vendor extractor in `nullrun.instrumentation.auto`.
The extractor handles both Cohere v1 (`prompt_tokens` /
`completion_tokens`) and v2 (`input_tokens` / `output_tokens`)
response shapes — see the `_cohere_extractor` docstring in
`src/nullrun/instrumentation/auto.py` for the field fallback.

> Cohere streaming does not include usage in the streamed chunks —
> only the non-streaming response carries it. Tracked events for
> streamed Cohere calls will report `tokens=0`.

## See also

- [Auto-instrumentation overview](auto-instrumented-frameworks.md)
- [Quickstart](../getting-started/quickstart.md)