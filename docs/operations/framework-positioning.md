---
title: Framework & ecosystem positioning
maturity: stable
description: How NullRun overlaps with framework-native human-in-the-loop patterns in LangGraph, LangChain, CrewAI, AutoGen, and OpenAI Agents — where it sits beside them, and what NullRun does not cover.
---

# Framework & ecosystem positioning

Teams that already run an agent framework ask two questions: what
does NullRun add, and where does it collide with what I have.

This page answers both. The short version: the frameworks own
**flow control**, NullRun owns **authorization**. The two layers
answer different questions, and exactly one of them — approval for a
sensitive tool — is a real overlap.

## The overlap matrix

| Layer | LangGraph | LangChain | CrewAI | AutoGen | OpenAI Agents | **NullRun** |
|---|---|---|---|---|---|---|
| **Flow-level HITL** — pause a graph step for input | `interrupt()` + `Command(resume=...)` | `interrupt_before` / `interrupt_after` | `human_input=True` per task | `HandoffMessage` | `RunHooks` | Sits **above** this layer, not instead of it |
| **Hard budget gate** — block before the call runs | — | — | — | — | — | Atomic cost reservation, period-bound, fail-closed |
| **Tool-call policy** — declarative block or allow | — | — | — | — | — | Policy list with pattern matching |
| **Immutable audit trail** — refusals included | Call trace only | Call trace only | — | — | Tracing only | Hash-chained log of gate decisions, kept separate from execution records |
| **Policy as data** — per organization, per workflow | — | — | — | — | — | Scopes and versions in the dashboard |

Two layers have no framework equivalent:

- **Budget and tool policy as enforcement.** A framework callback can
  observe a tool call. It cannot hold the call frame while a server
  decides.
- **An audit log of decisions.** A trace records what happened. It
  does not record that the call was *refused*, and it is not a
  tamper-evident chain.

One layer belongs to the frameworks alone:

- **Flow-level HITL.** NullRun does not manage graph state, and it
  does not decide whether the agent's plan is a good plan.

## The one real overlap: action-level approval

Both layers can ask a human about the same sensitive tool. They ask
different questions, and the people who answer them are usually
different.

| Layer | Question | When it fires | Who answers |
|---|---|---|---|
| Framework `interrupt()` | "Is this step right?" | Inside a node, around the model or tool call | The flow's operator, in Slack, a UI, or an IDE |
| NullRun approval | "Is this action allowed under this policy?" | Before the tool function body runs | The governance team, in the Approvals view |

Both can fire on one tool call. That is the design point, not a
conflict — a run can need both an operator who confirms the plan and
a governance team that authorizes the action.

### Where it bites

**Latency.** Every protected call adds one round trip to the gateway.
For batch agents this is invisible. For a latency-sensitive chat UI it
may matter. Two ways to reduce it:

- Protect only the calls that carry policy weight.
- Use the framework's own HITL for planning steps and NullRun
  approval for sensitive tool calls only.

**Two approval surfaces.** If both layers fire on the same tool, the
operator can see two prompts. Ways out:

- Join the framework's thread id and the NullRun `execution_id` in one
  dashboard view.
- Use framework HITL for planning and NullRun approval for sensitive
  invocations only.

**Conceptual confusion.** A team can have a complete framework HITL
setup and still overspend, still write to production without a
decision, and still have no enforcement log to show an auditor.

## Coexistence guidance

### LangGraph and LangChain

Keep your `interrupt()` nodes as they are. Add `@protect` on the tool
functions and on the model call site inside the node. The SDK attaches
to the framework on the first `@protect` call, so there is no patch to
install and no opt-in list to maintain.

### CrewAI

`human_input=True` on a task stays — it answers "is the framing
right?". Add `@protect` on tool calls that carry policy weight:
database writes, outbound email, payments. CrewAI has no budget gate,
so this is additive.

### AutoGen

Conversational HITL stays outside NullRun's scope. Wrap the agent
invocation site with `@protect`.

### OpenAI Agents

`RunHooks` stays for run-level lifecycle events. Add `@protect` on
the tool function itself. The SDK instruments `Runner.run` and
`Runner.run_streamed` automatically.

## What NullRun does not claim

These are outside the product by design, not gaps in the roadmap.

1. **Output moderation.** Content safety, PII redaction, prompt
   injection blocking. Use a model-side guardrail.
2. **Orchestration.** Graph state, DAG execution, and scheduling.
3. **Retrieval governance.** Vector store and retrieval quality.
4. **Network egress policy.** NullRun decides on call metadata. It
   does not inspect a tool payload for exfiltration.
5. **Provider-side cost reconciliation.** NullRun computes cost from
   the response it sees. The upstream webhook is the authority for
   what the provider billed.

If your evaluation includes one of these, NullRun is a complement.

## Gaps

- **Framework drift.** Framework HITL features move quickly. Check
  the vendor's current documentation for the framework you run.
- **No latency benchmark against framework HITL.** A framework pause
  is a process-local suspension. A NullRun decision is a network
  authorization call. The two numbers are not comparable, and
  NullRun's own p99 at production scale is not measured.
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
