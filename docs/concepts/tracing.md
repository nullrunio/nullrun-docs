---
title: Tracing
maturity: stable
description: Every protected call becomes a span, every run becomes a trace, and the control center renders the tree as a waterfall.
---

# Tracing

A **trace** is one run of your agent. A **span** is one step inside
it. The control center puts traces under **Executions** and **Traces** in
the sidebar.

When a user reports "the agent did something odd at 14:30", the trace
is where you look.

## What you see in the control center

The **Executions** page lists the executions your organization ran.
Each row shows the execution id, the action, the agent, the workflow,
the model, the tool, the token count, the result, the cost and the
time. The four counters above the table count gate decisions —
**Allow**, **Block**, **Pending** and **Denied**. A blocked call has no
row, because it produced no execution. The **CSV** button downloads the
rows on the screen as a CSV file.

<figure class="nr-shot">
  <img class="nr-shot__light" src="../../assets/images/screenshots/executions-light.png"
       alt="Executions page listing every agent run with workflow, duration, status and cost columns."
       loading="lazy" decoding="async">
  <img class="nr-shot__dark" src="../../assets/images/screenshots/executions-dark.png"
       alt="Executions page listing every agent run with workflow, duration, status and cost columns."
       loading="lazy" decoding="async">
  <figcaption class="nr-shot__caption">Executions</figcaption>
</figure>

The **Traces** page lists the runs. Above the table, four tiles count
the loaded runs, the ones that succeeded, the ones that errored, and
the median duration.

<figure class="nr-shot">
  <img class="nr-shot__light" src="../../assets/images/screenshots/traces-light.png"
       alt="Traces page with the waterfall of LLM and tool calls for a single execution."
       loading="lazy" decoding="async">
  <img class="nr-shot__dark" src="../../assets/images/screenshots/traces-dark.png"
       alt="Traces page with the waterfall of LLM and tool calls for a single execution."
       loading="lazy" decoding="async">
  <figcaption class="nr-shot__caption">Traces · Waterfall</figcaption>
</figure>

Open one and you get a header with the start time, the end time, the
total duration and the number of spans, with the error count
alongside it. Under the header is the waterfall.

The waterfall is the trace. Each row is one span:

- The **name** of the protected function
- A **duration bar**, positioned against the longest span in the trace
- A **status** — ok or error
- The **policy verdict** for that call, when the gate recorded one
- The **span id**, in the row tooltip. The audit log carries no span
  column, so you reach an audit row through the execution id.

Nested calls sit under their parent, so a supervisor that calls
sub-agents renders as one tree rather than several. Click a row to
pin its details.

## How spans are created

The SDK emits a span for every protected call. You do not add
instrumentation yourself.

```python
import nullrun

@nullrun.protect
def research(question):
    return call_llm(question)
```

A call to `research` opens a span and closes it when the call returns.
A protected call inside another protected call becomes a child span.

The context managers set the parent, so you control the shape of the
tree:

| Context manager | What it does |
|---|---|
| `with nullrun.workflow("name"):` | Sets the workflow for every call inside the block |
| `with nullrun.span("phase"):` | Names the phase; calls inside become its children |
| `with nullrun.agent("name"):` | Attributes the calls to one agent |

```python
import nullrun

with nullrun.workflow("support-bot"):
    with nullrun.span("research"):
        research(question)
```

LLM calls are reported separately from spans. The SDK sends the token
counts your provider reports, and the gateway prices them. The call
is attached to the span that was active when it happened.

## Identifiers

| Field | What it identifies |
|---|---|
| `trace_id` | One run. The same on every span in that run. |
| `span_id` | One protected call |
| `parent_span_id` | The span this one sits under |

Open a run by its `trace_id` in the trace URL. The audit log filters by
execution id, not by trace id.

## What is not stored

NullRun never persists prompt content or LLM response bodies. A span
carries the function name, the timing, the status and the verdict —
not the text you sent or the text you got back. The arguments of a
tool call are the exception, and they live on the event rather than
on the span. See
[Error handling → What is NOT stored](error-handling.md#what-is-not-stored).

## How long traces are kept

Traces follow your plan's retention window:

| Plan | Retention |
|---|---|
| Lite | 3 days |
| Starter | 7 days |
| Growth | 30 days |
| Scale | 90 days |
| Enterprise | Unlimited |

When a trace expires, the aggregated spend survives, summarised per
workflow per period.

Retention is separate from the volume caps. Lite also throttles to
**10 000 tokens per hour** and **75 000 executions per month**, so a
Lite workflow stops producing traces inside the 3-day window. See
[Billing & Plan → Caps](billing.md#caps).

Export the rows you need; the retention window removes them. The
**CSV** button on the Executions page writes the rows on the screen as
a CSV file, not the organization's whole history.

## Common questions

### "My trace shows nothing"

The runtime was never created, so no span was ever emitted. Check that
`NULLRUN_API_KEY` is set and that the first protected call actually
ran.

### "My trace is incomplete"

The SDK buffers events and flushes them on a timer. A process that
dies with the buffer unflushed loses the spans still in flight.
`init()` registers a clean shutdown at exit, so a normal exit reaches
the gateway.

### "One LLM call is counted twice"

The SDK's auto-instrumentation already reports the token counts for
the LLM clients it supports. If you also report the same call with
`get_runtime().track_llm(...)`, the call is booked twice. Pick one.

### "Why is my trace missing a step?"

The control center shows one span per protected call. A helper function
that is not decorated with `@protect` produces no span. Decorate every
call you want to see in the tree.

## See also

- [Workflows](workflow.md) — the `workflow()` context manager
- [Error handling](error-handling.md) — how errors map to spans
- [Budgets](budgets.md) — where the cost in a trace comes from
