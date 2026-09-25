---
title: Quickstart
description: Decorate your first tool with @protect and ship it through the NullRun gate in under thirty lines of code.
---

# Quickstart

Wrap any function with **`@nullrun.protect`** to track its cost, tools, and
behaviour, and let NullRun halt it when it goes off the rails.

```python title="app.py"
from openai import OpenAI
from nullrun import protect, workflow

client = OpenAI()

with workflow("my-first-agent"):       # scopes the gate to a workflow
    @protect                           # gates every call via /check;
    def answer(prompt: str) -> str:    # lazy-creates the runtime on first call
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content

if __name__ == "__main__":
    with nullrun.guard():         # catches NullRunError, prints the
        print(answer("What does NullRun do?"))
        # structured 4-line developer report on failure, then sys.exit(1)
```

> **First `@protect` call builds the runtime.** It reads
> `NULLRUN_API_KEY`, installs the HTTP instrumentation hook, and attaches
> every importable framework hook in a single idempotent step. If the
> API key is missing at that point, the SDK raises `NullRunConfigError`
> (NR-C001) at the first gate call.

> **`@protect` is the entry point.** For early fail-fast (CI / smoke
> tests) before the first `@protect` call, see [Reference → init](../reference/sdk-api.md#init).

> The `with workflow("..."):` block binds every `@protect` call inside
> to a named workflow — required, otherwise the SDK falls back to an
> ad-hoc workflow_id with no budget policy attached. For production,
> the workflow name should match the dashboard workflow your API key
> is bound to.

Every call inside `answer()` is cost-attributed and governed by your
workspace policy. On any policy outcome (budget cap, tool block, rate
limit, transport outage), `with nullrun.guard():` prints the structured
four-line developer report (`error_code` + what + where + why +
how to fix) and exits `1`.

## What gets tracked

- LLM tokens in and out
- Cost in cents (per-call and aggregate)
- Latency
- Tool calls (if you use a framework integration)

## What can go wrong

See [Troubleshooting](../troubleshooting.md) for the full table of
expected behaviours (budget cap, loop, sensitive-tool, gateway down,
kill/pause, etc.) and recovery steps. For the three-layer error model,
see [Concepts → Error handling](../concepts/error-handling.md).

## Next

- [Concepts → Circuit breaker](../concepts/circuit-breaker.md)
- [Concepts → Control plane](../concepts/control-plane.md)
- [Concepts → Error handling](../concepts/error-handling.md)
- [How-to → Set a hard cost cap](../how-to/cost-cap.md)
- [How-to → Use with LangGraph](../how-to/langgraph.md)
