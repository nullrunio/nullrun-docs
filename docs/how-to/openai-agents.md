---
title: Openai Agents
description: Install the nullrun[agents] extra and gate every tool call from an OpenAI Agents SDK workflow.
---

# Use with OpenAI Agents

Install (the OpenAI Agents framework hook is the only one that
needs a vendor package — `openai-agents`):

```bash title="shell"
pip install "nullrun[agents]" openai-agents
```

Wrap the `Runner.run_sync` call (or any sync / async runner) with
`@protect`. The runtime + `openai-agents` `RunHooks` /
`RunStreamedHooks` patch are attached lazily on the first `@protect`
call:

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

`@protect` tracks every tool call the agent makes and halts the run
if the workflow exceeds budget, hits a sensitive tool, or is
rate-limited by the policy.

## See also

- [Examples → OpenAI Agents](https://github.com/nullrunio/nullrun-examples/blob/master/examples/openai_agents_basic.py)
