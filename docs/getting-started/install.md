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

> **No manual initialization required.** Initialization is lazy,
> process-wide, and triggered by the first `@protect` call. There is
> no `init()` / `init_or_die()` boilerplate to add to your entry
> point — see the mental-model diagram in [Quickstart](quickstart.md).

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

on first use, so you only need to export the key as an environment
variable:

```bash title="shell"
export NULLRUN_API_KEY=nr_live_...
```

The SDK reads `NULLRUN_API_KEY` on the first `@protect` call (no
`init()` step). The HMAC secret is **not** a constructor argument —
it is read from `NULLRUN_SECRET_KEY` or returned by `/api/v1/auth/verify`.

> **Optional: explicit `init()` / `init_or_die()`.** The first
> `@protect` call creates the runtime lazily from `NULLRUN_API_KEY`.
> Explicit `init()` is only needed if you want to fail-fast on a
> missing key before the first gate call (CI / smoke tests), or to
> bind an API key from a non-env source. Most apps skip it.
> See [Reference → init / init_or_die](../reference/sdk-api.md#init--init_or_die-optional-early-fail-fast)
> for the contract.

For env-var setup (`NULLRUN_API_KEY`, `NULLRUN_SECRET_KEY`, and other
runtime flags), see [Configuration](configuration.md).

## Auto-instrumentation

The SDK's auto-instrumentation runs **lazily on the first protected
execution path**, not at import time or in any pre-`@protect` hook.
The lazy trigger creates the runtime, reads `NULLRUN_API_KEY`, installs
the HTTP instrumentation, and attaches every framework / transport
hook it can detect in `sys.modules` in a single process-wide
idempotent step.

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
