# Mistral

Install:

```bash title="shell"
pip install "nullrun[mistral]"
```

```python title="mistral_client.py"
import nullrun
from mistralai import Mistral

nullrun.init(api_key="nr_live_...")

client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])
resp = client.chat.complete(
    model="mistral-large-latest",
    messages=[{"role": "user", "content": "Hello"}],
)
```

Patched via the per-vendor extractor in `nullrun.instrumentation.auto`.
Mistral's API is OpenAI-compatible, so the same extractor that
handles `api.openai.com` handles `api.mistral.ai` — it pulls
`usage.prompt_tokens` / `usage.completion_tokens` from the response
body.

## Test coverage

Per NullRun's testing policy (see the SDK README), Mistral /
Gemini / Cohere / Bedrock patches have **extractor unit tests only**
— no full transport-to-track integration test. The per-vendor
extractor shape is exercised by isolated tests, but no
multi-roundtrip end-to-end test confirms the cost actually flows
through `/api/v1/track`. This is documented per §8 of the source-of-
truth positioning — verify behaviour against your real workload
before relying on it.