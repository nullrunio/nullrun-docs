# Use with OpenAI Agents

Install:

```bash title="shell"
pip install "nullrun[agents]" openai-agents
```

Wrap the `Runner.run_sync` call (or any sync / async runner) with
`@protect`:

```python title="openai_agents_protect.py"
from agents import Agent, Runner

from nullrun import init, protect

init(api_key="nr_live_...")


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

`@protect` tracks every tool call the agent makes and halts the run if
the workflow exceeds budget, loops, or hits a sensitive tool.

## See also

- [Examples → OpenAI Agents](https://github.com/nullrunio/nullrun-examples/blob/main/examples/openai_agents_basic.py)
