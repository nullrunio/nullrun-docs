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

## What gets tracked

- LLM tokens in and out
- Cost in cents (per-call and aggregate)
- Latency
- Tool calls (if you use a framework integration)
- Loop / retry patterns

## What can go wrong (and how NullRun reacts)

| Situation | Default behaviour |
| --- | --- |
| Workflow exceeds budget | Raise `BudgetExceededError` and stop |
| Agent in a loop | Raise `LoopDetectedException` and stop |
| Agent calls a sensitive tool | Require `STRICT` mode or block |
| Gateway unreachable | Use cached policy (if any) or PERMISSIVE |
| Sensitive tool + gateway unreachable | **Fail closed** — block the call |

## Next

- [Concepts → Circuit breaker](../concepts/circuit-breaker.md)
- [How-to → Set a hard cost cap](../how-to/cost-cap.md)
- [How-to → Use with LangGraph](../how-to/langgraph.md)
