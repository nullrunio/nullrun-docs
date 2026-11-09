---
title: OpenAI Agents
description: Gate an OpenAI Agents run with @protect, and let the SDK report the token counts of every model call the agent makes without manual tracking.
maturity: stable
---

# Use with OpenAI Agents

Install the framework next to the SDK. There is no NullRun vendor extra
for it.

```bash title="shell"
pip install nullrun openai-agents
```

The SDK attaches to the framework on its own. The attachment is
installed once per process — see [LLM frameworks](llm-frameworks.md)
for the rule. Import the `agents` package before that happens.

## The wiring

```python title="openai_agents_protect.py"
from agents import Agent, Runner

from nullrun import protect


@protect
def ask(prompt: str) -> str:
    agent = Agent(
        name="assistant",
        instructions="Answer in one sentence.",
    )
    result = Runner.run_sync(agent, prompt)
    return result.final_output


print(ask("What is the capital of France?"))
```

`@protect` runs the gate before the agent starts. The run is refused if
the workflow is out of budget, if a tool the agent calls is blocked, or
if the policy rate-limits the call.

The framework hook reports the token counts of every model call the
agent makes, so the spend lands on the workflow without any manual
tracking.

## See also

- [LLM frameworks](llm-frameworks.md) — the other supported frameworks
- [Examples → OpenAI Agents](https://github.com/nullrunio/nullrun-examples/blob/master/examples/openai_agents_basic.py)
