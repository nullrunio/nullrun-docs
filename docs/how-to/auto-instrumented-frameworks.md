# Auto-instrumented LLM frameworks

`nullrun.init()` patches the underlying HTTP transport (`httpx`) and
the agent framework modules it can detect in `sys.modules`. Every
patch wraps the vendor import in `try/except ImportError`, so you
can install one extra group without crashing on `init()`.

In every case, the call gets `track_llm` events automatically —
**no `@protect` required for cost tracking**. `@protect` is the
**gate** layer (budget pre-flight + kill/pause + sensitive-tool
decision).

> The Gemini vendor extra is `google-genai` (the actively maintained
> package, ≥ 1.0); the older `google.generativeai` package is **not**
> supported.

## Per-framework guides

Each framework has its own page with the install command, a
runnable snippet, and the exact patcher that handles it:

- [Anthropic](anthropic.md)
- [Mistral](mistral.md)
- [Gemini (Google GenAI)](gemini.md)
- [Cohere](cohere.md)
- [AWS Bedrock](bedrock.md)
- [LangChain](langchain.md)
- [LangGraph](langgraph.md)
- [LlamaIndex](llama-index.md)
- [CrewAI](crewai.md)
- [AutoGen](autogen.md)
- [Raw `openai` SDK](raw-openai.md)
- [OpenAI Agents SDK](openai-agents.md)

## Detection matrix

| Detected in `sys.modules` | Patcher |
| --- | --- |
| `openai` ≥ 1.0 | `instrumentation.auto` via the httpx transport hook |
| `openai-agents` | `instrumentation.auto.patch_openai_agents` |
| `anthropic` | `instrumentation.auto` via the httpx transport hook |
| `langgraph` | `instrumentation.auto.patch_langgraph_compiled` (wraps `Pregel.invoke` / `.stream` / `.ainvoke` / `.astream`) |
| `langchain` | `instrumentation.auto.patch_langchain_callback` (injects `NullRunCallback` into `BaseCallbackManager.__init__`) |
| `mistralai`, `google-genai`, `cohere`, `boto3` (bedrock) | per-vendor extractors |
| `llama_index`, `crewai`, `autogen_agentchat` | Phase 7 patches in `instrumentation.llama_index`, `crewai`, `autogen` |

If a vendor is missing from the table, the SDK still runs — it
simply has no extractor for that framework and the LLM call is
invisible to NullRun until you wrap it in `@protect`.

## All of the above

```bash title="shell"
pip install "nullrun[all]"
```

Installs every vendor extra. Useful for evaluation harnesses that
span multiple providers.