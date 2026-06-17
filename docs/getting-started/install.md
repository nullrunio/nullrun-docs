# Install

## Python SDK

```bash
pip install nullrun
```

Verify:

```bash
python -c "from nullrun import protect; print('ok')"
```

Current version: `0.4.0` (alpha).

> **No local mode.** If `init()` is called without an API key, the
> SDK raises `NullRunAuthenticationError` at first use. There is no
> offline / local-only fallback.

## API key + HMAC secret

Sign in at [app.nullrun.io](https://app.nullrun.io), open **Settings
→ API keys**, and create a key. Each key is minted with:

- `NULLRUN_API_KEY` (`nr_live_...`) — public identifier
- `NULLRUN_SECRET_KEY` — HMAC-SHA256 signing secret, shown **once** at
  creation

Pass both to `init()`:

```python
from nullrun import init

init(
    api_key="nr_live_...",
    secret_key="nrs_...",   # optional in dev, required in prod when
                            # NULLRUN_HMAC_REQUIRED=true
)
```

or via env vars:

```bash
export NULLRUN_API_KEY=nr_live_...
export NULLRUN_SECRET_KEY=nrs_...
```

Without the secret the SDK signs with a no-op fallback and emits a
`RuntimeWarning` — production deployments require it.

## Auto-instrumentation

`nullrun.init()` patches the underlying HTTP transport (`httpx`) and
the agent framework modules it can detect in `sys.modules`:

| Detected | Patcher |
| --- | --- |
| `openai` ≥ 1.0 | `instrumentation.auto.patch_openai` (httpx transport) |
| `openai-agents` | `instrumentation.auto.patch_openai_agents` |
| `anthropic` | `instrumentation.auto.patch_anthropic` |
| `langgraph` / `langchain` | `instrumentation.auto.patch_langgraph_compiled` |
| `mistralai`, `google-genai`, `cohere`, `boto3` (bedrock) | per-vendor extractors |

The Gemini vendor extra is `google-genai` (the actively maintained
package, ≥ 1.0); the older `google.generativeai` package is **not**
supported. Install with `pip install "nullrun[gemini]"`.

In every case, the call gets `track_llm` events automatically — no
`@protect` required for cost tracking. `@protect` is the **gate**
layer (budget pre-flight + kill/pause + sensitive-tool decision).

## Optional extras

| Extra | Installs |
| --- | --- |
| `nullrun[langgraph]` | `langgraph` |
| `nullrun[agents]` | `openai-agents` |
| `nullrun[openai]` | `openai` |
| `nullrun[anthropic]` | `anthropic` |
| `nullrun[mistral]` | `mistralai` |
| `nullrun[gemini]` | `google-generativeai` |
| `nullrun[cohere]` | `cohere` |
| `nullrun[bedrock]` | `boto3` |
| `nullrun[autogen]` | `pyautogen` |
| `nullrun[all]` | every vendor extra |

```bash
pip install "nullrun[langgraph]"
pip install "nullrun[all]"
```

> Note: `nullrun[openai]` is for the raw `openai` SDK — it is **not**
> the OpenAI Agents SDK. For agents use `nullrun[agents]`.

## Gateway (self-host)

If you want to run the gateway yourself instead of using the hosted
control plane, see
[`nullrunio/nullrun`](https://github.com/nullrunio/nullrun) and the
production deployment guide (`nullrun_vps_prod.md` in that repo).
