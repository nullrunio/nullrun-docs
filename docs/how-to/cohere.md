# Cohere

Install:

```bash title="shell"
pip install "nullrun[cohere]"
```

```python title="cohere_client.py"
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
response shapes, including the field fallback when one of the two
shapes is missing.

> Cohere streaming does not include usage in the streamed chunks —
> only the non-streaming response carries it. Tracked events for
> streamed Cohere calls will report `tokens=0`.

## Test coverage

Per NullRun's testing policy (see the SDK README), Cohere patches
have **extractor unit tests only** — no full transport-to-track
integration test. The extractor shape is exercised by isolated
tests, but no multi-roundtrip end-to-end test confirms the cost
actually flows through `/api/v1/track`. This is documented per §8
of the source-of-truth positioning — verify behaviour against your
real workload before relying on it.