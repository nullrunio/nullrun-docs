# Gemini (Google GenAI)

Install:

```bash title="shell"
pip install "nullrun[gemini]"
```

```python title="gemini_client.py"
import nullrun
from google import genai

nullrun.init(api_key="nr_live_...")

client = genai.Client()
resp = client.models.generate_content(
    model="gemini-2.0-flash",
    contents="Hello",
)
```

Requires the `google-genai` package (≥ 1.0). The legacy
`google.generativeai` import is **not** supported — see the install
guide for the rationale.

Patched via the per-vendor extractor in `nullrun.instrumentation.auto`.
The extractor reads `usageMetadata.promptTokenCount` /
`usageMetadata.candidatesTokenCount` from the response body.

## Test coverage

Per NullRun's testing policy (see the SDK README), Gemini patches
have **extractor unit tests only** — no full transport-to-track
integration test. The extractor shape is exercised by isolated
tests, but no multi-roundtrip end-to-end test confirms the cost
actually flows through `/api/v1/track`. This is documented per §8
of the source-of-truth positioning — verify behaviour against your
real workload before relying on it.