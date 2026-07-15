# Quickstart

Wrap any function with **`@nullrun.protect`** to track its cost, tools, and
behaviour, and let NullRun halt it when it goes off the rails.

```python title="app.py"
from openai import OpenAI
from nullrun import init_or_die, guarded, protect, shutdown

init_or_die(api_key="nr_live_...")        # exits cleanly if api_key missing
client = OpenAI()

@guarded                                # catches NullRunError, prints
@protect                                # the catalog user-message,
def answer(prompt: str) -> str:         # sys.exit(1) — zero boilerplate
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

That's it — every call inside `answer()` is now cost-attributed and
governed by your workspace policy. On any policy outcome (budget cap,
tool block, rate limit, transport outage), `@guarded` prints the
catalog wording on stderr and exits `1` — no `try/except NullRunError`
needed.

## What gets tracked

- LLM tokens in and out
- Cost in cents (per-call and aggregate)
- Latency
- Tool calls (if you use a framework integration)
- Loop / retry patterns

## What can go wrong

See [Troubleshooting](../troubleshooting.md) for the full table of
expected behaviours (budget cap, loop, sensitive-tool, gateway down,
kill/pause, etc.) and recovery steps. For the three-layer error model
and why the boilerplate stays at zero, see
[Concepts → Error handling](../concepts/error-handling.md).

## Next

- [Concepts → Circuit breaker](../concepts/circuit-breaker.md)
- [Concepts → Control plane](../concepts/control-plane.md)
- [Concepts → Error handling](../concepts/error-handling.md)
- [How-to → Set a hard cost cap](../how-to/cost-cap.md)
- [How-to → Use with LangGraph](../how-to/langgraph.md)