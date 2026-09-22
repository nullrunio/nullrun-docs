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

> **No local mode.** If `NULLRUN_API_KEY` is missing when the first
> `@protect` call hits the runtime, the SDK raises
> `NullRunConfigError` (NR-C001) at the gate. There is no offline /
> local-only fallback — the silent-no-op path was removed because it
> bypassed every backend gate.

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

> **Don't need `init()` at all?** The first `@protect` call creates
> the runtime lazily from `NULLRUN_API_KEY`. Explicit `init()` is
> optional and only needed if you want to fail-fast on a missing key
> before the first gate call, or to bind an API key from a non-env
> source. Most apps skip it.

For env-var setup (`NULLRUN_API_KEY`, `NULLRUN_SECRET_KEY`, and other
runtime flags), see [Configuration](configuration.md).

## Auto-instrumentation

The SDK's auto-instrumentation runs **lazily on the first `@protect`
call**, not at import or `init()` time. The lazy trigger creates the
runtime and patches every framework / transport hook it can detect in
`sys.modules` in a single process-wide idempotent step.

| Detected | Coverage |
| --- | --- |
| `openai` ≥ 1.0 | HTTP transport hook (httpx) |
| `openai-agents` | Agent framework hook (`Runner.run` / `run_streamed`) |
| `anthropic` | HTTP transport hook (httpx) |
| `langgraph` | Graph runtime hook (`Pregel.invoke` / `stream` / `ainvoke` / `astream`) |
| `langchain` | Callback manager hook (`BaseCallbackManager`) |
| `llama-index` | LlamaIndex tool/agent hook |
| `crewai` | CrewAI EventBus bridge (1.15+) |
| `autogen` | AutoGen agent runtime hook |
| `mistralai`, `google-genai`, `cohere`, `boto3` (bedrock) | per-vendor URL-keyed extractors |

The Gemini vendor extra is `google-genai` (the actively maintained
package, ≥ 1.0); the older `google.generativeai` package is **not**
supported.

In every case the call is cost-tracked automatically — `@protect` is
not required for tracking. `@protect` is the **gate** layer (budget
pre-flight + kill/pause + sensitive-tool decision).

### Zero-activity diagnostic

If `@protect` fires 50+ times without the runtime observing a single
`track_llm` event (i.e. your code path never reaches an LLM call, or
auto-instrumentation never attached), the SDK logs **one WARNING**
naming the three most likely root causes — no spam, warn-once.

## Optional extras

The plain `pip install nullrun` package covers every LLM provider
(OpenAI, Anthropic, Mistral, Gemini, Cohere, Bedrock) via URL-keyed
httpx extractors — those vendor SDKs are **never imported** by
NullRun. The extras below are only needed when NullRun has to call
into the vendor package directly (framework hooks, not HTTP hooks).

| Extra | Installs | When you need it |
| --- | --- | --- |
| `nullrun[agents]` | `openai-agents` | OpenAI Agents SDK framework hook |
| `nullrun[crewai]` | `crewai` | CrewAI EventBus bridge |
| `nullrun[langgraph]` | `langgraph` | LangGraph Pregel runtime hook |
| `nullrun[llama-index]` | `llama-index-core` | LlamaIndex dispatcher hook |
| `nullrun[autogen]` | `autogen-agentchat`, `autogen-ext[openai]` | AutoGen runtime hook |
| `nullrun[langchain]` | `langchain-core` | LangChain callback manager hook |
| `nullrun[opentelemetry]` | `opentelemetry-api`, `opentelemetry-sdk` | OTel span export |
| `nullrun[fastapi]` | `fastapi`, `starlette`, `httpx` | Server-framework integration |

```bash title="shell"
pip install "nullrun[langgraph]"
pip install "nullrun[crewai]"
```

> **Deprecated extras (kept for back-compat, no longer required):**
> `nullrun[openai]`, `nullrun[anthropic]`, `nullrun[mistral]`,
> `nullrun[gemini]`, `nullrun[cohere]`, `nullrun[bedrock]`. The SDK
> never imported those vendor packages for the HTTP-level path; the
> extras are now no-ops. URL-keyed httpx extractors cover all six
> without any vendor install.
