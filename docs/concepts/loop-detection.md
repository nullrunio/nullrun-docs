# Loop detection

A **loop** is when the agent calls the same tool with the same
arguments repeatedly without making progress. Loops burn budget
without producing useful work — every iteration spends tokens
but doesn't move the task forward.

The loop detector catches this and blocks the agent before the
budget is wasted. In the dashboard, a loop shows up in **Decision
History** as repeated `block` decisions with reason `LOOP_DETECTED`.

## What is a loop?

The detector triggers when the same tool is called with the same
arguments more than `loop_threshold` times in `loop_window_secs`.
The defaults are 6 calls in 60 seconds — both are policy fields
you can override per workflow.

Examples of what counts as a loop:

- `tavily_search("latest LLM benchmarks")` called 10 times in a
  minute → loop detected, agent blocked
- `read_file("/etc/passwd")` called 8 times in 40 seconds → loop
  detected
- The agent calls `tavily_search` 5 times with different queries →
  not a loop (different arguments)
- The agent calls `tavily_search` 4 times with the same query,
  then `read_file` 3 times → not a loop (different tools)

The detector is **content-aware**: it compares the arguments, not
just the tool name. Two calls to `tavily_search("foo")` and
`tavily_search("bar")` are different.

## Why loops happen

Common causes:

- **The agent's prompt doesn't include enough context** to know it
  already searched for something
- **The tool returns ambiguous results** and the agent retries
  hoping for different output
- **A retry loop** — the agent's framework retries on failure but
  the failure isn't transient
- **A bug in the agent** — the tool returns success but the agent
  doesn't update its internal state

Most loops are fixable: improve the prompt, dedupe tool results
inside the agent, or detect "same args" before calling.

## What the agent sees

When a loop is detected, the SDK raises `NullRunBlockedException`
with reason `LOOP_DETECTED`. The agent's loop dies on the next
iteration:

```python
from nullrun import NullRunBlockedException

try:
    for _ in range(100):
        search_results = search(prompt)
        # agent forgets to update prompt — calls search() with same prompt
except NullRunBlockedException:
    # Loop detected. Stop and ask the user for guidance.
    return "I'm stuck in a loop — could you clarify what you're looking for?"
```

With `@guarded`, the SDK prints a friendly message and exits with
code 1. The agent dies cleanly.

## How to configure loop detection

Two policy fields control the detector:

| Field | Default | What it does |
|---|---|---|
| `loop_threshold` | `6` | Number of identical calls in the window that triggers detection |
| `loop_window_secs` | `60` | Time window for counting |

To make the detector more or less strict, edit the workflow's
policy in **Governance → Policies**. Lower the threshold for stricter
detection; raise it if your agent legitimately makes repeated calls
(e.g. polling for status).

The detector uses **most-restrictive-wins** — if you have an
org-scope policy with `loop_threshold: 3` and a workflow-scope
policy with `loop_threshold: 10`, the effective threshold is 3.

## What the dashboard shows

When a loop is detected, you'll see:

- **Decision History** — a row with `decision = block`,
  `reason = LOOP_DETECTED`, the tool name, and the argument hash
  (so you can see which call repeated).
- **Workflow status** — the workflow doesn't auto-pause or kill
  on a loop block. The agent's code decides whether to retry or
  give up. If the agent has `@guarded`, it exits and the workflow
  stays **Active** waiting for the next user request.
- **Audit log** — the full history of loop blocks for this
  workflow.

## What to do when you see repeated loops

Open the workflow's **Traces** tab and look at the failing
execution. Walk through:

1. **Which tool is looping?** — the trace shows the tool name and
   arguments on every call.
2. **Are the arguments identical?** — if yes, the agent's prompt
   isn't progressing. If different, the detector might be too
   sensitive (lower `loop_threshold` won't help; raise it).
3. **What's the agent trying to do?** — the trace's prompt content
   shows the agent's reasoning. Look for "I'll try again" or
   "let me search for..." patterns that suggest the agent doesn't
   know it already searched.

Common fixes:

- **Add deduplication** in the agent — before calling a tool,
  check if you've already called it with the same args in the
  current trace.
- **Improve the prompt** — tell the agent "before calling a tool,
  check your previous tool results".
- **Switch to a different model** — some models are more prone to
  loops than others.
- **Lower the loop threshold** — catch loops earlier, give the
  agent less rope to hang itself.

## Related: anomaly detection

The loop detector catches **structural** repetition (same tool,
same args). The **anomaly detector** (Growth+ plan) catches
**statistical** outliers — sudden spikes in cost, latency, or token
count that don't match the workflow's normal pattern.

See [Anomaly detection](anomaly-detection.md) for the broader
picture.

## See also

- [Circuit breaker](circuit-breaker.md) — what happens when loops
  trip the breaker
- [Anomaly detection](anomaly-detection.md) — the statistical
  cousin of loop detection
- [Tracing](tracing.md) — how to read the trace to understand the
  loop
- [Policies](policies.md) — how `loop_threshold` and
  `loop_window_secs` are configured
