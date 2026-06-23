# Auto-instrumented LLM frameworks

`nullrun.init()` patches the underlying HTTP transport (`httpx`) and
the agent framework modules it can detect in `sys.modules`. Every
patch wraps the vendor import in `try/except ImportError`, so you
can install one extra group without crashing on `init()`.

In every case below, the call gets `track_llm` events
automatically — **no `@protect` required for cost tracking**.
`@protect` is the **gate** layer (budget pre-flight + kill/pause +
sensitive-tool decision).

> The Gemini vendor extra is `google-genai` (the actively maintained
> package, ≥ 1.0); the older `google.generativeai` package is **not**
> supported.

## Anthropic

```bash
pip install "nullrun[anthropic]"
```

```python
import nullrun
from anthropic import Anthropic

nullrun.init(api_key="nr_live_...")

client = Anthropic()
resp = client.messages.create(
    model="claude-3-5-sonnet-latest",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello"}],
)
```

Patched via the `httpx` transport hook in `instrumentation.auto`.

## Mistral

```bash
pip install "nullrun[mistral]"
```

```python
import nullrun
from mistralai import Mistral

nullrun.init(api_key="nr_live_...")

client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])
resp = client.chat.complete(
    model="mistral-large-latest",
    messages=[{"role": "user", "content": "Hello"}],
)
```

Patched via the per-vendor extractor in `instrumentation.auto`.

## Gemini (Google GenAI)

```bash
pip install "nullrun[gemini]"
```

```python
import nullrun
from google import genai

nullrun.init(api_key="nr_live_...")

client = genai.Client()
resp = client.models.generate_content(
    model="gemini-2.0-flash",
    contents="Hello",
)
```

Requires the `google-genai` package (≥ 1.0). The legacy
`google.generativeai` import is not supported.

## Cohere

```bash
pip install "nullrun[cohere]"
```

```python
import nullrun
import cohere

nullrun.init(api_key="nr_live_...")

client = cohere.Client()
resp = client.chat(
    model="command-r-plus",
    message="Hello",
)
```

## AWS Bedrock

```bash
pip install "nullrun[bedrock]"
```

```python
import nullrun
import boto3

nullrun.init(api_key="nr_live_...")

client = boto3.client("bedrock-runtime", region_name="us-east-1")
resp = client.converse(
    modelId="anthropic.claude-3-sonnet-20240229-v1:0",
    messages=[{"role": "user", "content": [{"text": "Hello"}]}],
)
```

Patched at the `boto3` transport layer; works for every model
hosted on Bedrock (Anthropic, Mistral, Cohere, Meta, AI21, etc.).

## LangChain

```bash
pip install "nullrun[langchain]"
```

```python
import nullrun
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

nullrun.init(api_key="nr_live_...")

llm = ChatOpenAI(model="gpt-4o-mini")
resp = llm.invoke([HumanMessage(content="Hello")])
```

The same auto-instrumentation path works for any LangChain
`Runnable` (chains, agents, retrievers).

## LlamaIndex

```bash
pip install "nullrun[llama-index]"
```

```python
import nullrun
from llama_index.core.llms import ChatMessage
from llama_index.llms.openai import OpenAI

nullrun.init(api_key="nr_live_...")

llm = OpenAI(model="gpt-4o-mini")
resp = llm.chat([ChatMessage(role="user", content="Hello")])
```

## CrewAI

```bash
pip install "nullrun[crewai]"
```

```python
import nullrun
from crewai import Agent, Crew, Task

nullrun.init(api_key="nr_live_...")

researcher = Agent(
    role="Researcher",
    goal="Answer the question",
    backstory="Concise and accurate.",
)

task = Task(
    description="What does NullRun do?",
    agent=researcher,
    expected_output="Two sentences.",
)

crew = Crew(agents=[researcher], tasks=[task])
result = crew.kickoff()
```

## AutoGen

```bash
pip install "nullrun[autogen]"
```

```python
import nullrun
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient

nullrun.init(api_key="nr_live_...")

model = OpenAIChatCompletionClient(model="gpt-4o-mini")
assistant = AssistantAgent("assistant", model_client=model)
result = await assistant.run(task="Hello")
```

## Raw `openai` SDK

If you use the `openai` package directly (no LangChain / LlamaIndex /
CrewAI on top), install the OpenAI extra:

```bash
pip install "nullrun[openai]"
```

```python
import nullrun
from openai import OpenAI

nullrun.init(api_key="nr_live_...")
client = OpenAI()
resp = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Hello"}],
)
```

> Note: `nullrun[openai]` is for the raw `openai` SDK — it is **not**
> the OpenAI Agents SDK. For the latter, use `nullrun[agents]`.

## OpenAI Agents SDK

```bash
pip install "nullrun[agents]"
```

See [Use with OpenAI Agents](openai-agents.md) for the full walkthrough.

## LangGraph

```bash
pip install "nullrun[langgraph]"
```

See [Protect a LangGraph agent](langgraph.md) for the full
walkthrough (StateGraph + auto-instrumentation).

## All of the above

```bash
pip install "nullrun[all]"
```

Installs every vendor extra. Useful for evaluation harnesses that
span multiple providers.

## Detection matrix

| Detected in `sys.modules` | Patcher |
| --- | --- |
| `openai` ≥ 1.0 | `instrumentation.auto` via the httpx transport hook |
| `openai-agents` | `instrumentation.auto.patch_openai_agents` |
| `anthropic` | `instrumentation.auto` via the httpx transport hook |
| `langgraph` / `langchain` | `instrumentation.auto.patch_langgraph_compiled` |
| `mistralai`, `google-genai`, `cohere`, `boto3` (bedrock) | per-vendor extractors |
| `llama_index`, `crewai`, `autogen_agentchat` | Phase 7 patches in `instrumentation.llama_index`, `crewai`, `autogen` |

If a vendor is missing from the table, the SDK still runs — it
simply has no extractor for that framework and the LLM call is
invisible to NullRun until you wrap it in `@protect`.
