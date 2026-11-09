---
title: Install
description: Install the NullRun Python SDK, create an API key, and see what gets instrumented automatically.
maturity: stable
---

# Install

## Install the SDK

```bash title="shell"
pip install nullrun
```

The package needs Python 3.10 or newer. It depends on `httpx` and nothing else.

```bash title="shell"
python -c "from nullrun import protect; print('ok')"
```

## Create an API key

Sign in at [nullrun.io](https://nullrun.io). Open **Access → API keys** and click **New API key**. The dialog asks for a name, a workflow, and an expiration.

The key is enough. The SDK signs its requests with the key and fetches the matching signing secret from `POST /api/v1/auth/verify` on first use. Without a key the SDK raises `NullRunAuthenticationError` with the code `NR-C001`.

```bash title="shell"
export NULLRUN_API_KEY=nr_live_...
```

Set `NULLRUN_SECRET_KEY` yourself only if your secret manager already holds the signing secret.

## What gets instrumented

Instrumentation attaches when the runtime starts. It patches the HTTP client and every framework it finds in `sys.modules`.

| Package | What the SDK attaches |
| --- | --- |
| `httpx` | Token counting for every provider built on it |
| `requests` | Token counting through `Session.send` |
| `langchain-core` | Callback manager and chat model hooks |
| `openai-agents` | `Runner.run` and `Runner.run_sync` |
| `langgraph` | `Pregel.invoke`, `stream`, `ainvoke`, `astream` |
| `llama-index` | LLM chat-end and function-call events |
| `crewai` | `Crew.kickoff` and `kickoff_async` |
| `autogen` | `BaseChatAgent.on_messages` and the OpenAI chat client |

Provider traffic is recognised by host, not by package:

| Host | Provider |
| --- | --- |
| `api.openai.com` | OpenAI |
| `openai.azure.com` | Azure OpenAI |
| `api.anthropic.com` | Anthropic |
| `generativelanguage.googleapis.com` | Gemini |
| `api.cohere.ai` | Cohere |
| `api.mistral.ai` | Mistral |
| `bedrock-runtime.amazonaws.com` | Bedrock |

NullRun never imports a vendor package. Install the vendor package you already use.

## Frameworks

Install the framework next to the SDK. No extra is needed for any of them.

```bash title="shell"
pip install nullrun langgraph langchain-openai
pip install nullrun crewai
pip install nullrun openai-agents
```

## Optional extras

| Extra | Installs | When you need it |
| --- | --- | --- |
| `nullrun[websocket]` | `websockets` | Real-time workflow state push. Without it the SDK polls the gateway for state changes, and a kill or pause takes longer to reach the agent. |
| `nullrun[opentelemetry]` | `opentelemetry-api`, `opentelemetry-sdk` | Exporting spans to an OpenTelemetry collector. |
| `nullrun[dev]` | `pytest`, `pytest-asyncio`, `respx`, `mypy`, `ruff`, `coverage`, `httpx` | Running the SDK test suite locally. |

```bash title="shell"
pip install "nullrun[websocket]"
```

## If the dashboard stays empty

The SDK logs one warning when `@protect` has run 50 times and the SDK has seen no LLM call. The gate is enforced, but no cost is booked. The usual causes are a raw `httpx` client outside the instrumented surface, a custom transport, or a framework that is not on the list above.

## Next

- [Quickstart → your first gated call](quickstart.md)
- [Configuration → every setting](configuration.md)
- [Reference → init](../reference/sdk-api.md#init)
