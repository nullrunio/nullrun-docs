# CrewAI

Install:

```bash title="shell"
pip install "nullrun[crewai]"
```

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

Patched via `nullrun.instrumentation.crewai.patch_crewai`, which
hooks the CrewAI agent's LLM-call path so every task emits a
`track_llm` event with the underlying model's usage. The vendor
import is wrapped in `try/except ImportError` so installing only
this extra group does not crash on `init()`.

## See also

- [Auto-instrumentation overview](auto-instrumented-frameworks.md)
- [Quickstart](../getting-started/quickstart.md)