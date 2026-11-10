---
title: Framework & ecosystem positioning
maturity: stable
description: Where NullRun sits beside an agent framework: what the SDK instruments, where approval overlaps with framework HITL, and what NullRun does not cover.
---

# Framework & ecosystem positioning

Teams that already run an agent framework ask two questions: what
does NullRun add, and where does it collide with what I have.

This page answers both. The short version: the framework owns **flow
control**, NullRun owns **authorization**. One of them — approval for a
sensitive tool — is a real overlap.

## The layers

Two layers belong to the framework:

- **Flow control.** Graph state, node order, scheduling.
- **Flow-level HITL.** Pausing a step and waiting for input.

NullRun does not manage graph state, and it does not decide whether the
agent's plan is a good plan.

Four layers belong to NullRun. The gateway enforces all of them.

| Layer | What it does |
|---|---|
| **Hard budget gate** | Reserves the cost of a call before it runs, against a period-bound counter. A refusal stops the call. |
| **Tool-call policy** | A declarative list of block and allow patterns, matched on the tool name. |
| **Immutable audit trail** | A hash-chained log of gate decisions, kept separate from execution records. A refusal is in it. |
| **Policy as data** | Scopes and versions in the control center, per organization and per workflow. |

NullRun sits above the framework layer. It does not replace it.

## What the SDK instruments automatically

`nullrun.init()` installs the patches. There is no patch to install
and no opt-in list to maintain.

| Path | What the SDK patches | Gate check |
|---|---|---|
| `httpx` | The `httpx.Client` and `httpx.AsyncClient` transports | Before the request |
| `requests` | `requests.Session.send` | Before the request |
| LangChain | `BaseCallbackManager` | On the model call |
| LangChain | `BaseChatModel.invoke`, `ainvoke`, `stream`, `astream` | On the model call |
| LangGraph | `Pregel.invoke`, `stream`, `ainvoke`, `astream` | On the model call |
| OpenAI Agents | `Runner.run`, `Runner.run_sync` | None |
| LlamaIndex | The `llama_index.core` dispatcher | None |
| CrewAI | `Crew.kickoff`, `Crew.kickoff_async`, and the event bus | None |
| AutoGen | `BaseChatAgent.on_messages` and `OpenAIChatCompletionClient.create` | None |

Where there is no gate check, the SDK still records the call, so the
cost reaches the ledger. Put `@protect` on the tools that carry policy
weight.

## The one real overlap: action-level approval

Both layers can ask a human about the same sensitive tool. They ask
different questions, and the people who answer them are usually
different.

| Layer | Question | When it fires | Who answers |
|---|---|---|---|
| Framework HITL | "Is this step right?" | Inside a node, around the model or tool call | The flow's operator |
| NullRun approval | "Is this action allowed under this policy?" | Before the tool function body runs | The governance team, in the Approvals view |

Both can fire on one tool call. That is the design point, not a
conflict — a run can need both an operator who confirms the plan and a
governance team that authorizes the action.

### Where it bites

**Latency.** Every protected call adds one round trip to the gateway.
For batch agents this is invisible. For a latency-sensitive chat UI it
may matter. Two ways to reduce it:

- Protect only the calls that carry policy weight.
- Use the framework's own HITL for planning steps and NullRun
  approval for sensitive tool calls only.

**Two approval surfaces.** If both layers fire on the same tool, the
operator can see two prompts. One way out: use the framework's HITL for
planning and NullRun approval for sensitive invocations only.

**Conceptual confusion.** A team can have a complete framework HITL
setup and still overspend, still write to production without a
decision, and still have no enforcement log to show an auditor.

## Coexistence guidance

### LangGraph and LangChain

Keep your own HITL nodes as they are. Add `@protect` on the tool
functions and on the model call site inside the node. `nullrun.init()`
installs the framework patches, so there is nothing to wire up.

### CrewAI

Keep your own human-input step. It answers "is the framing right?".
Add `@protect` on tool calls that carry policy weight: database writes,
outbound email, payments. The CrewAI patch records the run's cost, so
`@protect` is what gates the calls.

### AutoGen

Conversational HITL stays outside NullRun's scope. Wrap the agent
invocation site with `@protect`.

### OpenAI Agents

Keep your run-level lifecycle hooks. Add `@protect` on the tool
function itself. The SDK instruments `Runner.run` and `Runner.run_sync`
automatically.

## What NullRun does not claim

These are outside the product by design, not gaps in the roadmap.

1. **Output moderation.** Content safety, PII redaction, prompt
   injection blocking. Use a model-side guardrail.
2. **Orchestration.** Graph state, DAG execution, and scheduling.
3. **Retrieval governance.** Vector store and retrieval quality.
4. **Network egress policy.** NullRun decides on call metadata. It
   does not inspect a tool payload for exfiltration.
5. **Provider-side cost reconciliation.** NullRun prices the tokens it
   records against its own pricing table. It does not compare that
   number with the provider's invoice.

If your evaluation includes one of these, NullRun is a complement.

## Gaps

- **Framework drift.** Framework HITL features move quickly. Check the
  vendor's current documentation for the framework you run.
- **No latency benchmark against framework HITL.** A framework pause is
  a process-local suspension. A NullRun decision is a network
  authorization call. The two numbers are not comparable, and NullRun's
  own p99 at production scale is not measured.
- **No empirical study of approval friction.** The mitigations above
  are design guidance. Teams running both layers should compare the
  two surfaces before committing.
- **No automatic link between a framework thread id and a NullRun
  `execution_id`.** The two ids have different shapes, and joining
  them is on the adopter.

## See also

- [Performance & limits](performance.md) — timeouts, rate limits, and
  the fail-closed posture
- [Protect a LangGraph agent](../how-to/langgraph.md)
- [Use with OpenAI Agents](../how-to/openai-agents.md)
- [Use CrewAI](../how-to/crewai.md)
- [LLM frameworks](../how-to/llm-frameworks.md)
- [Human approval](../concepts/human-approval.md)
- [Sensitive tools](../concepts/sensitive-tools.md)
- [Budgets](../concepts/budgets.md)
