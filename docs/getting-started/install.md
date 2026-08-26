---
title: Install
description: Install the NullRun Python SDK with pip, create an API key in the dashboard, and verify the gate is reachable from your environment.
---

# Install

## Python SDK

```bash title="shell"
pip install nullrun
```

Verify:

```bash title="shell"
python -c "from nullrun import protect; print('ok')"
```

> **No local mode.** If `init()` is called without an API key, the
> SDK raises `NullRunAuthenticationError` at first use. There is no
> offline / local-only fallback.

## API key

Sign in at [nullrun.io](https://nullrun.io), open **API keys**, and create a key. Each key is minted with a public
identifier (`nr_live_...`) plus a server-side HMAC secret. The SDK
transparently obtains the HMAC secret via:
```http
POST /api/v1/auth/verify
```

on first use, so you only need to pass the API key:

```python title="app.py"
import nullrun
nullrun.init(api_key="nr_live_...")
```

The public `init()` surface takes `api_key` (and optionally `api_url`,
`debug`). The HMAC secret is **not** a constructor argument — it is
read from `NULLRUN_SECRET_KEY` or returned by `/api/v1/auth/verify`.

For env-var setup (`NULLRUN_API_KEY`, `NULLRUN_SECRET_KEY`, and other
runtime flags), see [Configuration](configuration.md).

## Auto-instrumentation

`nullrun.init()` patches the underlying HTTP transport (`httpx`) and
the agent framework modules it can detect in `sys.modules`:

| Detected | Coverage |
| --- | --- |
| `openai` ≥ 1.0 | HTTP transport hook |
| `openai-agents` | Agent framework hook |
| `anthropic` | HTTP transport hook |
| `langgraph` | Graph runtime hook (`invoke` / `stream` / `ainvoke` / `astream`) |
| `langchain` | Callback manager hook |
| `mistralai`, `google-genai`, `cohere`, `boto3` (bedrock) | per-vendor extractors |

The Gemini vendor extra is `google-genai` (the actively maintained
package, ≥ 1.0); the older `google.generativeai` package is **not**
supported. Install with `pip install "nullrun[gemini]"`.

In every case the call is cost-tracked automatically — `@protect` is
not required for tracking. `@protect` is the **gate** layer (budget
pre-flight + kill/pause + sensitive-tool decision).

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

```bash title="shell"
pip install "nullrun[langgraph]"
pip install "nullrun[all]"
```

> Note: `nullrun[openai]` is for the raw `openai` SDK — it is **not**
> the OpenAI Agents SDK. For agents use `nullrun[agents]`.
