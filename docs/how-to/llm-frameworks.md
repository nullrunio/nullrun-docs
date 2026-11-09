---
title: LLM frameworks
description: Which LLM providers and agent frameworks the SDK instruments on its own, and what to do when it misses a call.
maturity: stable
---

# LLM frameworks

The SDK attaches to the HTTP client and to the agent frameworks it
finds installed. The attachment happens once per process: on `init()`
and on the first `@protect` call.

Two layers, and they do different work:

| Layer | What it does |
|---|---|
| Cost tracking | Reports the token counts of every LLM call |
| Gate | Refuses a call that breaks budget, policy, or the control plane |

Cost tracking runs on its own. `@protect` is what turns a tracked call
into a gated one.

## Providers

Provider coverage is keyed on the request host. The SDK never imports
a vendor package to cover it, so there is no vendor extra to install.

| Host | Provider |
|---|---|
| `api.openai.com` | OpenAI |
| `openai.azure.com` | Azure OpenAI |
| `api.anthropic.com` | Anthropic |
| `api.mistral.ai` | Mistral |
| `generativelanguage.googleapis.com` | Google Gemini |
| `api.cohere.ai` | Cohere |
| `bedrock-runtime.amazonaws.com` | AWS Bedrock |

A sub-domain of one of these hosts matches too. The OpenAI and
Mistral responses share one shape, so one extractor covers both.

The SDK reports token counts. The gateway prices the call from the
model name and the org's pricing policy.

## Frameworks

Each framework hook is a no-op when the package is not installed.

| Package | What the hook covers |
|---|---|
| `httpx` | Every HTTP client built on it, including the OpenAI and Anthropic SDKs |
| `requests` | Every client built on the `requests` library |
| `langchain` | Chat-model calls, including in-memory mock providers |
| `langgraph` | Compiled graphs, on every run mode |
| `openai-agents` | The runner, with the token counts of each model call |
| `crewai` | Crew, agent, and task lifecycle events, plus the run's usage totals |
| `llama-index` | LlamaIndex query and chat calls |
| `autogen-agentchat` | AutoGen agent and team calls |

Install the SDK once, then install the frameworks you use:

```bash title="shell"
pip install nullrun langgraph langchain-openai openai-agents crewai
```

## A runnable example

```python title="tracked_call.py"
from langchain_openai import ChatOpenAI
from nullrun import protect

llm = ChatOpenAI(model="gpt-4o-mini")


@protect
def ask(prompt: str) -> str:
    return llm.invoke(prompt).content


print(ask("What is the capital of France?"))
```

The framework hook reports the token counts of the call inside
`ask`. The `@protect` wrapper gates it.

## When the SDK cannot see the call

| Symptom | Cause | Fix |
|---|---|---|
| No cost shows up for a provider | The host is not in the table above | Report the call by hand |
| No cost shows up for a custom client | The client does not use `httpx` or `requests` | Report the call by hand |
| The call is tracked twice | A manual report sits next to an automatic one | Drop the manual report |

Reporting a call by hand means calling `runtime.track_llm(...)`. See
[Manual cost and event tracking](custom-tracking.md).

Do not report a call the SDK already sees. The two reports add up.

## See also

- [Protect a LangGraph agent](langgraph.md)
- [Use with OpenAI Agents](openai-agents.md)
- [Use with CrewAI](crewai.md)
- [Manual cost and event tracking](custom-tracking.md)
