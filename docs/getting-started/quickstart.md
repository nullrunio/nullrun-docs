# Quickstart

Wrap any function with `@protect` to track its cost, tools, and
behaviour, and let NullRun halt it when it goes off the rails.

```python title="app.py"
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

## What can go wrong

See [Troubleshooting](../troubleshooting.md) for the full table of
expected behaviours (budget cap, loop, sensitive-tool, gateway down,
kill/pause, etc.) and recovery steps.

## Next

- [Concepts → Circuit breaker](../concepts/circuit-breaker.md)
- [Concepts → Control plane](../concepts/control-plane.md)
- [How-to → Set a hard cost cap](../how-to/cost-cap.md)
- [How-to → Use with LangGraph](../how-to/langgraph.md)
