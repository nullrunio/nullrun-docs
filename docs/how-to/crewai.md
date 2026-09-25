---
title: Crewai
description: Wrap CrewAI tools and tasks with @protect so the NullRun gate evaluates every crew action before it executes.
---

# CrewAI

Install (the SDK declares `crewai>=0.80,<2.0`; the guide targets
**CrewAI 1.15+**, which exposes the EventBus subsystem used for
lifecycle event tracking):

```bash title="shell"
pip install nullrun crewai
```

The patch subscribes to the crewai `EventBus` and translates each
lifecycle event into a `nullrun.track(...)` call. The runtime and the
crewai EventBus hook are attached lazily on the first
`@protect` call:

```python title="crewai_crew.py"
import nullrun
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

The CrewAI integration automatically tracks crew / agent / task /
tool lifecycle events. Token totals still come from the crew's usage
metrics after kickoff — the SDK reports the canonical
`(model, prompt_tokens, completion_tokens)` tuple on every billable
row.

When crewai's events module is not importable (a stripped-down
third-party build), only the per-event span bridge is
skipped; the post-run cost attribution still works.

## See also

- [LLM frameworks](llm-frameworks.md)
- [Quickstart](../getting-started/quickstart.md)
