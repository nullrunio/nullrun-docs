# Quickstart

Wrap any function with `@protect` to track its cost, tools, and
behaviour, and let NullRun halt it when it goes off the rails.

```python
from openai import OpenAI
from nullrun import init, protect

init(api_key="nr_live_...")
client = OpenAI()

@protect
def answer(prompt: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content

print(answer("What does NullRun do?"))
```

That's it — every call inside `answer()` is now cost-attributed and
governed by your workspace policy.

> Without an `api_key`, `init()` raises `NullRunAuthenticationError` at
> first use. There is no local / offline mode — NullRun has no way to
> enforce anything without the gateway.

## What gets tracked

- LLM tokens in and out
- Cost in cents (per-call and aggregate)
- Latency
- Tool calls (if you use a framework integration)
- Loop / retry patterns

## What can go wrong (and how NullRun reacts)

| Situation | Default behaviour | Exception |
| --- | --- | --- |
| Workflow exceeds budget | Halt at next gate call | `NullRunBlockedException` |
| Agent in a loop | Halt at next gate call | `NullRunBlockedException` |
| Agent calls a sensitive tool | Block the call | `NullRunBlockedException` |
| Gateway unreachable | Allow (PERMISSIVE fallback) | (none — call proceeds) |
| Sensitive tool + gateway unreachable | **Fail closed** — block the call | `NullRunBlockedException` |
| Workflow killed via dashboard | Raise at next gate call | `WorkflowKilledInterrupt` (BaseException) |
| Workflow paused via dashboard | Raise at next gate call | `WorkflowPausedException` |

See [Errors](../reference/errors.md) for the full exception hierarchy.

## Next

- [Concepts → Circuit breaker](../concepts/circuit-breaker.md)
- [Concepts → Control plane](../concepts/control-plane.md)
- [How-to → Set a hard cost cap](../how-to/cost-cap.md)
- [How-to → Use with LangGraph](../how-to/langgraph.md)
