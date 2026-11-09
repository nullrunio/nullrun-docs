---
title: CrewAI
description: Gate a CrewAI crew run with @protect and let the SDK report the crew's cost.
maturity: stable
---

# Use with CrewAI

Install CrewAI next to the SDK. There is no NullRun vendor extra for
it.

```bash title="shell"
pip install nullrun crewai
```

The SDK attaches to CrewAI on its own. The attachment happens on
`init()` and on the first `@protect` call.

## The wiring

```python title="crewai_crew.py"
from crewai import Agent, Crew, Task
from nullrun import protect

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


@protect
def run_crew() -> str:
    return str(crew.kickoff())


print(run_crew())
```

`@protect` runs the gate once, at the start of the crew run. The run
is refused if the workflow is out of budget, if the policy rate-limits
the call, or if the workflow is paused or killed.

Individual CrewAI tool executions are reported as events. They are not
evaluated against the tool policy on their own.

## What the SDK reports

| Source | What it reports |
|---|---|
| The CrewAI event bus | Crew, agent, and task lifecycle events |
| `crew.usage_metrics` | One LLM cost row per model, read after the run returns |

The event bus path needs CrewAI 1.15 or newer. On an older release the
lifecycle events are skipped and the usage totals still arrive.

## See also

- [LLM frameworks](llm-frameworks.md)
- [Multi-agent orchestration](multi-agent-orchestration.md)
- [Quickstart](../getting-started/quickstart.md)
