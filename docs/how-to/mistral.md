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

## See also

- [Auto-instrumentation overview](auto-instrumented-frameworks.md)
- [Quickstart](../getting-started/quickstart.md)