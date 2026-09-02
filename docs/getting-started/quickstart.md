---
title: Quickstart
description: Decorate your first tool with @protect and ship it through the NullRun gate in under thirty lines of code.
---

# Quickstart

Wrap any function with **`@nullrun.protect`** to track its cost, tools, and
behaviour, and let NullRun halt it when it goes off the rails.

```python title="app.py"
from openai import OpenAI
from nullrun import init_or_die, guarded, protect, workflow, shutdown

init_or_die(api_key="nr_live_...")        # exits cleanly if api_key missing
client = OpenAI()

with workflow("my-first-agent"):       # scopes the gate to a workflow
    @guarded                           # catches NullRunError, prints
    @protect                           # the catalog user-message,
    def answer(prompt: str) -> str:    # sys.exit(1) — zero boilerplate
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content

if __name__ == "__main__":
    try:
        print(answer("What does NullRun do?"))
    finally:
        shutdown()
```

> The `with workflow("..."):` block binds every `@protect` call inside
> to a named workflow — required, otherwise the SDK falls back to an
> ad-hoc workflow_id with no budget policy attached. For production,
> the workflow name should match the dashboard workflow your API key
> is bound to.

Every call inside `answer()` is cost-attributed and governed by your
workspace policy. On any policy outcome (budget cap, tool block, rate
limit, transport outage), `@guarded` prints the catalog wording on
stderr and exits `1`.

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