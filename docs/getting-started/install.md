# Install

## Python SDK

```bash
pip install nullrun
```

Verify:

```bash
python -c "from nullrun import protect; print('ok')"
```

Current version: `0.6.0` (alpha).

> **No local mode.** If `init()` is called without an API key, the
> SDK raises `NullRunAuthenticationError` at first use. There is no
> offline / local-only fallback.

## API key

Sign in at [nullrun.io](https://nullrun.io), open **Settings
→ API keys**, and create a key. Each key is minted with a public
identifier (`nr_live_...`) plus a server-side HMAC secret. The SDK
transparently obtains the HMAC secret via `POST /api/v1/auth/verify`
on first use, so you only need to pass the API key:

```python
import nullrun

nullrun.init(api_key="nr_live_...")
```

For self-hosted gateways, or if you want to skip the auth round-trip,
set both via env vars before `init()`:

```bash
export NULLRUN_API_KEY=nr_live_...
export NULLRUN_SECRET_KEY=nrs_...   # optional: server-issued HMAC secret
```

The public `init()` surface takes `api_key` (and optionally `api_url`,
`debug`). The HMAC secret is **not** a constructor argument — it is
read from `NULLRUN_SECRET_KEY` or returned by `/api/v1/auth/verify`.

## Auto-instrumentation

`nullrun.init()` patches the underlying HTTP transport (`httpx`) and
the agent framework modules it can detect in `sys.modules`:

| Detected | Patcher |
| --- | --- |
| `openai` ≥ 1.0 | `instrumentation.auto` via the httpx transport hook |
| `openai-agents` | `instrumentation.auto.patch_openai_agents` |
| `anthropic` | `instrumentation.auto` via the httpx transport hook |
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
| `nullrun[opentelemetry]` | `opentelemetry-api`, `opentelemetry-sdk` |
| `nullrun[langgraph]` | `langgraph` |
| `nullrun[openai]` | `openai` |
| `nullrun[anthropic]` | `anthropic` |
| `nullrun[mistral]` | `mistralai` |
| `nullrun[gemini]` | `google-genai` |
| `nullrun[cohere]` | `cohere` |
| `nullrun[bedrock]` | `boto3` |
| `nullrun[agents]` | `openai-agents` |
| `nullrun[langchain]` | `langchain-core` |
| `nullrun[llama-index]` | `llama-index-core` |
| `nullrun[crewai]` | `crewai` |
| `nullrun[autogen]` | `autogen-agentchat`, `autogen-ext[openai]` |
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
