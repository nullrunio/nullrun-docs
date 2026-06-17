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

Sign in at [nullrun.io](https://nullrun.io), open **Settings
→ API keys**, and create a key. Each key is minted with:

- `NULLRUN_API_KEY` (`nr_live_...`) — public identifier
- `NULLRUN_SECRET_KEY` — HMAC-SHA256 signing secret, shown **once** at
  creation

Pass both to `init()` — the public `init()` surface takes
`api_key` only; the secret key is read from the `NULLRUN_SECRET_KEY`
env var, not from a constructor argument:

```python
import os
from nullrun import init

# Recommended: keep the secret key out of source by reading from env.
# In dev, the SDK signs with a no-op fallback and emits a
# RuntimeWarning when the secret is missing.
os.environ.setdefault("NULLRUN_SECRET_KEY", "nrs_...")

init(api_key="nr_live_...")
```

or set both via env vars before `init()`:

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
| `nullrun[gemini]` | `google-genai` |
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

The hosted control plane at [nullrun.io](https://nullrun.io) is the
recommended path for most teams. Self-hosting the gateway is also
available — see the gateway repository's deployment guide (the repo
itself is private; access is granted on request via
[support@nullrun.io](mailto:support@nullrun.io)).
