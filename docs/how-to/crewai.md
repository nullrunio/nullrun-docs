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

The patch lives at `nullrun.instrumentation.crewai` and subscribes
to the following crewai events via
`crewai_event_bus.scoped_listener(EventBusListener)`:

| Event | Track event emitted |
| --- | --- |
| `CrewKickoffStartedEvent` / `CrewKickoffCompletedEvent` | `span_start` / `span_end` per crew kickoff |
| `AgentExecutionStartedEvent` / `AgentExecutionCompletedEvent` | `span_start` / `span_end` per agent |
| `TaskStartedEvent` / `TaskCompletedEvent` / `TaskFailedEvent` | `span_start` / `span_end` per task |
| `LLMCallStartedEvent` / `LLMCallCompletedEvent` | `span_start` / `span_end` per LLM call |
| `ToolUsageStartedEvent` / `ToolUsageFinishedEvent` | `span_start` / `span_end` per tool call |

Token totals still come from `crew.usage_metrics` post-kickoff —
the post-run `track_llm` emission is unchanged so the dashboard
sees the canonical `(model, prompt_tokens, completion_tokens)`
tuple on every billable row.

When `crewai.events` is not importable (pre-1.15 crewai or a
stripped-down third-party build), the post-run `usage_metrics`
wrap is still installed and the patch returns `True` so callers
that gate on `"did nullrun.init register a crewai bridge"` keep
getting a positive answer; only the per-event span bridge is a
no-op.

## See also

- [LLM frameworks](llm-frameworks.md)
- [Quickstart](../getting-started/quickstart.md)
