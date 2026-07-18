# Multi-agent orchestration

When one agent delegates to sub-agents — a LangGraph supervisor, a
CrewAI crew, an OpenAI Agents `Runner` with handoffs, or a custom
orchestrator — NullRun tracks each sub-agent independently under the
same workflow.

The rule is: **one workflow = one budget pool, but the orchestration
tree is visible in the decision log and cost breakdown.**

## LangGraph supervisor → sub-agents

```python title="langgraph_orchestrator.py"
from typing import TypedDict
from langgraph.graph import END, StateGraph
from langchain_openai import ChatOpenAI

import nullrun
from nullrun import init_or_die, protect, workflow, shutdown

init_or_die()
llm = ChatOpenAI(model="gpt-4o-mini")


class State(TypedDict):
    topic: str
    research: str
    draft: str


@protect
def research_node(state: State) -> State:
    """Sub-agent — its @protect is a gate for the LLM call only."""
    out = llm.invoke(f"Research {state['topic']}")
    return {"research": out.content}


@protect
def writer_node(state: State) -> State:
    out = llm.invoke(f"Write a draft using: {state['research']}")
    return {"draft": out.content}


def supervisor(state: State) -> str:
    return END  # or "research" / "writer"


# Pin the whole orchestrator under one workflow_id. Every sub-agent
# call lands on the same workflow's budget.
with workflow("research-supervisor"):
    graph = StateGraph(State)
    graph.add_node("research", research_node)
    graph.add_node("writer", writer_node)
    graph.add_conditional_edges("supervisor", supervisor)
    graph.set_entry_point("supervisor")
    app = graph.compile()

    result = app.invoke({"topic": "LLM cost trends"})


if __name__ == "__main__":
    try:
        app.invoke({"topic": "LLM cost trends"})
    finally:
        shutdown()
```

`@protect` on each sub-agent ensures the gate runs before the LLM
call. The `with workflow("research-supervisor")` block scopes every
call to one workflow_id so the budget cap is enforced once across the
whole tree — the supervisor cannot accidentally blow past the cap by
fanning out.

## CrewAI crew

```python title="crewai_orchestrator.py"
import nullrun
from crewai import Agent, Crew, Process, Task
from nullrun import init_or_die, protect, workflow, shutdown

init_or_die()


@protect
def run_research_crew(topic: str) -> str:
    researcher = Agent(
        role="researcher",
        goal="Find facts about the topic",
        backstory="Concise, factual.",
    )
    writer = Agent(
        role="writer",
        goal="Draft an article from the research",
        backstory="Engaging prose.",
    )
    research_task = Task(
        description=f"Find 5 facts about {topic}",
        expected_output="Bullet list of facts.",
        agent=researcher,
    )
    write_task = Task(
        description="Write a 200-word article using the facts.",
        expected_output="Article body.",
        agent=writer,
    )

    # One workflow for the whole crew, one budget pool.
    with workflow("article-crew"):
        crew = Crew(
            agents=[researcher, writer],
            tasks=[research_task, write_task],
            process=Process.sequential,
        )
        return str(crew.kickoff())


if __name__ == "__main__":
    try:
        run_research_crew("LLM cost trends")
    finally:
        shutdown()
```

Each CrewAI agent's LLM call passes through the auto-instrumentation
hook. `track_llm` events arrive at the gateway under your workflow,
all counted against the same `budget_cents`.

## OpenAI Agents SDK with handoffs

```python title="openai_agents_orchestrator.py"
import nullrun
from agents import Agent, Runner
from nullrun import init_or_die, protect, workflow, shutdown

init_or_die()


@protect
def run_triage(query: str) -> str:
    billing = Agent(
        name="billing-agent",
        instructions="Answer billing questions only.",
        handoff_description="Routes billing queries.",
    )
    technical = Agent(
        name="technical-agent",
        instructions="Answer technical questions only.",
        handoff_description="Routes technical queries.",
    )
    triage = Agent(
        name="triage",
        instructions="Route the user to billing or technical.",
        handoffs=[billing, technical],
    )

    # Each Runner.run inside this workflow shares the budget pool.
    with workflow("support-triage"):
        result = Runner.run_sync(triage, query)
        return result.final_output


if __name__ == "__main__":
    try:
        run_triage("Where is my invoice?")
    finally:
        shutdown()
```

## What you see in the dashboard

For the LangGraph example, the **Workflow → Decisions** view shows:

- 1 entry per `@protect` invocation
- All entries share `workflow_id = "research-supervisor"`
- The audit trail lists the orchestration tree in the order LLM
  calls happened

For per-sub-agent cost attribution, use distinct `workflow_id`s —
but then you have multiple budget pools and the supervisor must
explicitly enforce the cap:

```python title="seperate_workflows.py"
with workflow("research-supervisor"):
    with workflow("research-subagent") as research_wf:
        research_node(state)  # counts against research-subagent's budget
    with workflow("writer-subagent") as writer_wf:
        writer_node(state)    # counts against writer-subagent's budget
```

This is the **opposite** pattern — useful when sub-agents have
independent budget allocations (e.g. one sub-agent handles paid API
calls, another is read-only), but you lose the "one cap protects
everything" guarantee.

## Operator kill across the tree

When an operator hits **Kill** in the dashboard, the WS push
delivers a `state_change(killed)` to **every** connected SDK client
holding the workflow's key. If multiple `@protect` calls are in-flight
across the orchestration tree, they all receive the kill signal at
their next yield boundary. See
[Control plane → kill contract](../concepts/control-plane.md#how-the-sdk-reacts)
for the wire-level details.

## Common pitfalls

| Pitfall | Symptom | Fix |
|---|---|---|
| Missing `with workflow(...)` around the orchestrator | Each sub-agent gets its own ad-hoc workflow_id, budget cap not enforced across the tree | Wrap the whole tree in one workflow block |
| Each sub-agent has its own key | Sub-agents share nothing — kill signal only reaches the one bound to the killed workflow | Use one key for the orchestrator and let sub-agents inherit |
| Catching `Exception` instead of `BaseException` around the orchestration loop | Kill signal swallowed, agents keep running | Catch `WorkflowKilledInterrupt` explicitly first |

## See also

- [Workflow context](../concepts/workflow.md) — how `workflow()` scopes events
- [Chain context](../concepts/workflow.md#chain-context-soft-mode-budget-gate) — soft mode for multi-step orchestrations
- [Use with LangGraph](langgraph.md) — single-agent LangGraph example
- [Use with OpenAI Agents](openai-agents.md) — single-agent example
