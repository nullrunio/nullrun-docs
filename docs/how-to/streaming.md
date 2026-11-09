---
title: Streaming responses
description: Gate a streamed LLM response, keep the chain alive while the stream runs, and report the cost of a stream.
maturity: stable
---

# Stream LLM responses

Two things make streaming different from a normal call: the response
arrives in pieces, and the run can take longer than a single gate
decision covers.

## Protect the call, not the generator

`@protect` wraps a function call. A function that yields is not a call
that finishes: the body runs later, when the caller iterates. The SDK
has no generator support, so a protected generator runs its body
outside the gate.

Protect the function that opens the stream instead. The gate runs when
the stream is created:

```python title="stream_answer.py"
import uuid

from openai import AsyncOpenAI
from nullrun import chain, protect

client = AsyncOpenAI()


@protect
async def open_stream(prompt: str):
    return await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        stream=True,
    )


async def answer(prompt: str):
    chain_id = str(uuid.uuid4())
    with chain(chain_id, op="start"):
        stream = await open_stream(prompt)
        async for chunk in stream:
            yield chunk.choices[0].delta.content or ""
```

The alternative is to protect each step of the loop. That gives the
gate one decision per chunk, which costs a round trip per chunk.

## Keep the chain alive

A chain closes after five minutes without a protected call, or when
`max_chain_duration_seconds` is exceeded. It defaults to 3600 seconds.

Send a heartbeat while the stream runs. `ping_chain` schedules them on
a wall-clock timer and returns a callable that stops the schedule:

```python title="stream_with_heartbeat.py"
import uuid

from openai import AsyncOpenAI
from nullrun import chain, get_runtime, protect

client = AsyncOpenAI()


@protect
async def open_stream(prompt: str):
    return await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        stream=True,
    )


async def answer(prompt: str):
    runtime = get_runtime()
    chain_id = str(uuid.uuid4())
    with chain(chain_id, op="start"):
        stop = runtime.ping_chain(chain_id)
        try:
            stream = await open_stream(prompt)
            async for chunk in stream:
                yield chunk.choices[0].delta.content or ""
        finally:
            stop()
```

`ping_chain` sends a heartbeat every 30 seconds by default. The
interval must stay between 10 and 120 seconds.

### Chain heartbeat

The interval is wall-clock, not chunk-based. One chunk per minute still
gets a heartbeat, and a fast stream does not flood the server.

A failed heartbeat is logged and ignored. The chain then closes when
its idle window runs out.

## What the SDK does with the chunks

The HTTP client you use decides how the chunks reach your code.

| HTTP client | When the chunks reach your code | Cost tracked for you |
|---|---|---|
| `httpx` | After the whole body has been read | Yes |
| `requests` | As they arrive | No |

The OpenAI and Anthropic SDKs are built on `httpx`. The SDK reads the
body in full so it can read the usage block that arrives in the last
chunk. The chunks then reach your code together.

The `requests` path leaves a streamed body alone, so the chunks arrive
in real time. The SDK cannot read the usage block, so it reports the
call as untracked and the cost stays at zero.

## Report a stream by hand

Report the call yourself when the SDK does not see it. Use
`stream_options={"include_usage": True}` so the last chunk carries the
usage block:

```python title="track_stream.py"
from openai import OpenAI
from nullrun import get_runtime

client = OpenAI()


def stream_with_cost(prompt: str):
    stream = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        stream=True,
        stream_options={"include_usage": True},
    )
    final = None
    for chunk in stream:
        final = chunk
        yield chunk.choices[0].delta.content or ""

    usage = getattr(final, "usage", None)
    if usage:
        get_runtime().track_llm(
            input_tokens=usage.prompt_tokens,
            output_tokens=usage.completion_tokens,
            model="gpt-4o-mini",
        )
```

A report the SDK already made adds the tokens a second time. Report a
call once.

## Kill during a stream

An operator kill reaches the SDK over the control-plane connection. It
surfaces at the next protected call.

| Protected function | What propagates |
|---|---|
| Async | `WorkflowKilledInterrupt` |
| Sync | `NullRunBlockedException` with `error_code` `NR-W002` |

A chunk loop over an open stream holds no protected call, so the kill
lands on the next stream you open. Catch it by name and close the
stream:

```python title="kill_handling.py"
from nullrun import WorkflowKilledInterrupt


async def answer(prompt: str):
    stream = None
    try:
        stream = await open_stream(prompt)
        async for chunk in stream:
            yield chunk.choices[0].delta.content or ""
    except WorkflowKilledInterrupt:
        if stream is not None:
            await stream.close()
        raise
```

## See also

- [Chain context](../concepts/workflow.md#chain-context)
- [Errors → SDK exception hierarchy](../reference/errors.md#sdk-exception-hierarchy)
- [Manual cost and event tracking](custom-tracking.md)
