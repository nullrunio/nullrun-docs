---
title: Quickstart
description: Send your first LLM call through the NullRun gate in three steps.
maturity: stable
---

# Quickstart

Install the SDK, export an API key, decorate one function.

## 1. Install

```bash title="shell"
pip install nullrun
```

## 2. Export an API key

Create a key in the dashboard under **Access → API keys**. Every key is bound to one workflow.

```bash title="shell"
export NULLRUN_API_KEY=nr_live_...
```

## 3. Decorate one function

`@protect` is the only decorator. It works on sync functions and on async functions.

```python title="app.py"
import nullrun
from openai import OpenAI
from nullrun import protect

client = OpenAI()


@protect
def answer(prompt: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    with nullrun.guard():
        print(answer("What does NullRun do?"))
```

`import nullrun` gives you `nullrun.guard()`. `from nullrun import protect` gives you the decorator.

## 4. Run it

```bash title="shell"
python app.py
```

## What the gate does

`@protect` sends a gate request when the protected function is called. The gateway checks:

- the budget of the workflow your API key is bound to
- the tool rules that match the call
- the rate limit

If the gateway allows the call, the function body runs. The SDK then tracks the input tokens, the output tokens, and the cost.

## What a refusal looks like

`with nullrun.guard():` catches every refusal. It writes the user-facing message and a developer report to stderr. The report carries the error code, the stage that failed, the endpoint, the reason, and the fix. The process exits with code `1`.

```
You've reached the usage limit for this conversation. Please try again later.
```

## Start the runtime yourself

`init()` is optional. The first `@protect` call creates the runtime from `NULLRUN_API_KEY`.

```python title="app.py"
import nullrun

nullrun.init()
```

Call it when you want a missing key to fail at startup rather than at the first request. A missing key raises `NullRunAuthenticationError` with the code `NR-C001`. `init()` also registers a clean shutdown on process exit.

## What gets tracked

- LLM tokens in and out
- Cost per call
- Latency
- Tool calls made through an instrumented framework

## Next

- [Install → optional extras](install.md#optional-extras)
- [First agent → the full walkthrough](onboarding.md)
- [Configuration → every setting](configuration.md)
- [Troubleshooting → every refusal and its fix](../troubleshooting.md)
- [Concepts → Circuit breaker](../concepts/circuit-breaker.md)
- [Concepts → Control plane](../concepts/control-plane.md)
- [Concepts → Error handling](../concepts/error-handling.md)
- [How-to → Set a hard cost cap](../how-to/cost-cap.md)
