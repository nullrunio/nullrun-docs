# CrewAI

Install (CrewAI **1.15+** required):

```bash title="shell"
pip install "nullrun[crewai]"
```

The current patch subscribes to the crewai `EventBus` and translates
each lifecycle event into a `runtime.track_event` call.

```python title="crewai_crew.py"
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

The CrewAI integration automatically tracks crew / agent / task /
tool lifecycle events. Token totals still come from the crew's usage
metrics after kickoff — the SDK reports the canonical
`(model, prompt_tokens, completion_tokens)` tuple on every billable
row.

When crewai's events module is not importable (pre-1.15 crewai or a
stripped-down third-party build), only the per-event span bridge is
skipped; the post-run cost attribution still works.

## See also

- [LLM frameworks](llm-frameworks.md)
- [Quickstart](../getting-started/quickstart.md)
