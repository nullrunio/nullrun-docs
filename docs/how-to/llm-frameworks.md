---
title: LLM frameworks
maturity: stable
description: Coverage matrix for OpenAI, Anthropic, Mistral, Gemini, Cohere, Bedrock, LangChain, LlamaIndex, CrewAI, AutoGen, and the raw openai SDK.
---
# LLM frameworks

The SDK's auto-instrumentation runs **lazily on the first `@protect`
call**, not at import or `init()` time. The lazy trigger creates the
runtime and walks `sys.modules` looking for known framework packages,
applying each detected patch in a single process-wide idempotent step.

In every case, the LLM call gets `track_llm` events automatically —
**no `@protect` required for cost tracking**. `@protect` is the
**gate** layer (budget pre-flight + kill / pause / sensitive-tool
decision).

> **HTTP-level coverage is the foundation.** OpenAI, Anthropic,
> Mistral, Gemini, Cohere, and Bedrock are covered by URL-keyed httpx
> extractors — the SDK never imports those vendor packages, so no
> extra is required. The extras below are only needed when NullRun
> has to call into the vendor package directly (framework hooks, not
> HTTP hooks).

> The Gemini vendor extra is `google-genai` (the actively maintained
> package, ≥ 1.0); the older `google.generativeai` package is **not**
> supported.

## Coverage matrix

| Provider | Install extra | Auto-instrumented | Tested end-to-end | Patcher |
| --- | --- | --- | --- | --- |
| OpenAI (`openai`) | none — httpx URL-keyed | ✅ | ✅ | `httpx` transport hook |
| Anthropic (`anthropic`) | none — httpx URL-keyed | ✅ | ✅ | `httpx` transport hook |
| OpenAI Agents (`openai-agents`) | `nullrun[agents]` | ✅ | ✅ | `patch_openai_agents` |
| Mistral (`mistralai`) | none — httpx URL-keyed | ✅ | ⚠️ extractor only | per-vendor extractor |
| Gemini (`google-genai`) | none — httpx URL-keyed | ✅ | ⚠️ extractor only | per-vendor extractor |
| Cohere (`cohere`) | none — httpx URL-keyed | ✅ | ⚠️ extractor only | per-vendor extractor |
| AWS Bedrock (`boto3`) | none — httpx URL-keyed | ✅ | ⚠️ extractor only | `httpx` extractor on `bedrock-runtime.amazonaws.com` |
| LangChain (`langchain`) | `nullrun[langchain]` | ✅ | ✅ | `patch_langchain_callback` |
| LangGraph (`langgraph`) | `nullrun[langgraph]` | ✅ | ✅ | `patch_langgraph_compiled` (auto on first `@protect` call) |
| LlamaIndex (`llama-index`) | `nullrun[llama-index]` | ✅ | ⚠️ extractor only | `instrumentation.llama_index` |
| CrewAI (`crewai`) | `nullrun[crewai]` | ✅ | ⚠️ extractor only | `instrumentation.crewai` |
| AutoGen (`autogen-agentchat`) | `nullrun[autogen]` | ✅ | ⚠️ extractor only | `instrumentation.autogen` |

> "Tested end-to-end" means: a multi-roundtrip test exists that
> verifies tokens flow from the vendor response into `/api/v1/track`.
> "Extractor only" means the unit test covers the JSON parsing, but
> no full integration test confirms the bytes-on-the-wire → track
> chain. Verify against your real workload before relying on it.

## Install everything

```bash title="shell"
pip install "nullrun[all]"
```

Installs every vendor extra (the ones that actually pull a vendor
package — `[agents]`, `[crewai]`, `[langgraph]`, `[langchain]`,
`[llama-index]`, `[autogen]`). The `[all]` meta-extra lives at
`pyproject.toml` and pulls every individual extra in one go.

## How the httpx transport hook works

The httpx transport hook wraps the response handler for any HTTP
client built on `httpx` (the `openai` SDK and the `anthropic` SDK
both use `httpx` under the hood). On every response, the hook:

1. Reads the JSON body.
2. Extracts token counts from the vendor's `usage` block
   (`usage.prompt_tokens` / `usage.completion_tokens` for OpenAI,
   `usage.input_tokens` / `usage.output_tokens` for Anthropic).
3. Emits a `track_llm` event with the extracted tokens.

The backend recomputes cost from the org's pricing policy — the
SDK only reports token counts, never dollar amounts.

## Detection logic

If your framework is installed, the SDK patches it automatically on
the **first `@protect` call**. The detection logic walks
`sys.modules` looking for known packages — `openai`, `openai-agents`,
`anthropic`, `langgraph`, `langchain`, `mistralai`, `google-genai`,
`cohere`, `boto3` (bedrock), `llama_index`, `crewai`,
`autogen_agentchat` — and applies the appropriate patch.

Order matters: if your code imports `openai` before the first
`@protect` call, the hook is in place before the first request. If
you import after the first `@protect` call, the SDK may not see the
late import — call `nullrun.patch()` explicitly to force a re-scan.

## Provider-specific notes

### Anthropic

Reasoning tokens (for o1-style extended-thinking models) are tracked
at the reasoning rate configured in your pricing policy. The hook
reads `usage.reasoning_tokens` when present.

### Mistral

The hook watches `mistralai` ≥ 1.0 (`MistralClient` and
`MistralAsyncClient`). Earlier `mistralai<1` clients have a
different response shape; the extractor handles both with a
duck-type check on `usage.prompt_tokens` / `usage.completion_tokens`.

### Bedrock

Bedrock uses AWS event streams (`InvokeModelWithResponseStream`),
not plain JSON responses. The hook attaches to the `boto3`
event-stream parser. Token counts come from
`invocationMetrics.inputTokenCount` / `outputTokenCount` in the
final `messageStop` event. **Streaming-only** — non-streaming
Bedrock calls must be reported via `track_llm` manually.

### LangGraph

The `nullrun[langgraph]` extra wraps `Pregel.invoke` / `.ainvoke` /
`.stream` / `.astream` so every node that calls an LLM goes through
the gate. The patch is auto-applied on the first `@protect` call.
See [Protect a LangGraph agent](langgraph.md) for the canonical
wiring pattern.

### CrewAI / AutoGen

Multi-agent frameworks spawn sub-agents that each make their own
LLM calls. The hook fires per call, so cost attribution lands in the
right `agent_id` automatically (the framework passes `agent_name`
through to the SDK contextvar).

## When auto-instrumentation can't see the call

Some patterns bypass the auto-instrumentation:

- Custom HTTP transport (not `httpx`) — use [`track_llm`](../reference/sdk-api.md#track_llm-manual-usage)
- Streaming chunks where the SDK is constructed before the first `@protect` call — call
  `nullrun.patch()` after the late imports
- A framework not listed above — file an issue at
  `github.com/nullrunio/nullrun-sdk-python`

The catch-all `track_llm(input_tokens=…, output_tokens=…, model=…)`
is the escape hatch for any of these. If `@protect` fires 50+ times
without the runtime seeing a single `track_llm` event, the SDK logs
**one** WARNING naming the three most likely root causes.

## See also

- [Protect a LangGraph agent](langgraph.md) — full LangGraph example
- [Use with OpenAI Agents](openai-agents.md) — `openai-agents` extra
- [Use with FastAPI](fastapi.md) — request-scoped SDK context
- [Manual cost / event tracking](custom-tracking.md) — `track_llm` / `track_tool` / `track_event`
