---
title: Streaming
description: Use @protect on a stream iterator so the gate's Cancel decision can stop a live response the moment an overrun is detected.
---

# Stream LLM responses

The SDK tracks streaming responses correctly — every chunk is
forwarded to your caller in real time, and the cost is reported from
the final chunk (which carries the `usage` block).

## The pattern

```python title="streaming_agent.py"
import nullrun
from openai import AsyncOpenAI
from nullrun import init_or_die, protect

init_or_die()
client = AsyncOpenAI()


@protect
async def stream_answer(prompt: str):
    stream = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        stream=True,
    )
    async for chunk in stream:
        yield chunk.choices[0].delta.content or ""
```

The transport hook reads the final `usage` block before emitting
`/track`, while forwarding chunks to your caller in real time.

## Long streams and soft mode

A long stream that exceeds the chain idle TTL (300s) will be killed
mid-chunk. The SDK sends a wall-clock heartbeat every **30 seconds**
per policy (configurable in `[10s, 120s]`) — not per chunk. For
multi-minute responses, use a `chain` context to keep the gate
alive:

```python
@protect
def long_stream(prompt: str):
    with chain("my-long-stream", op="start"):
        stream = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )
        for chunk in stream:
            yield chunk.choices[0].delta.content or ""
```

For budget headroom, set `enforcement_mode = "Soft"` on the policy.
See
[Chain context](../concepts/workflow.md#chain-context).

### Chain heartbeat

The SDK keeps the chain alive with a wall-clock heartbeat every
**30 seconds** by default (configurable per policy in `[10s, 120s]`).
The interval is time-based, not chunk-based: a slow stream with one
chunk per minute still gets a heartbeat; a fast stream does not spam
them.

If the chain dies (idle TTL expired, max duration exceeded, or
`op="end"`), the SDK raises `WorkflowKilledInterrupt` at the next
`yield` boundary.

## Kill signal mid-stream

An operator hit on **Kill** raises `WorkflowKilledInterrupt` at the
next `yield` boundary. It is a `BaseException` — catch it before any
`except Exception` block, otherwise you'll swallow the kill.

```python
from nullrun import WorkflowKilledInterrupt

@protect
async def stream_kill_safe(prompt: str):
    stream = await client.chat.completions.create(
        model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}],
        stream=True,
    )
    try:
        async for chunk in stream:
            yield chunk.choices[0].delta.content or ""
    except WorkflowKilledInterrupt:
        await stream.close()
        raise
```

## Tracking without auto-instrumentation

If the SDK's httpx transport hook can't see your custom streaming
client (a vendor SDK that bypasses httpx), call `track_llm` manually
after the stream ends. Use `stream_options={"include_usage": True}`
so the final chunk carries the usage block; otherwise you have to
estimate. See
[OpenAI streaming reference](https://platform.openai.com/docs/api-reference/chat-streaming).

```python
from nullrun import init_or_die, protect, track_llm


@protect
def custom_stream(prompt: str):
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
    if final and getattr(final, "usage", None):
        track_llm(
            input_tokens=final.usage.prompt_tokens,
            output_tokens=final.usage.completion_tokens,
            model="gpt-4o-mini",
        )
```

Without `track_llm()` the budget counter is never credited and the
next `/gate` may reject the next call based on stale spend.

## Common pitfalls

| Pitfall | Symptom | Fix |
|---|---|---|
| Heartbeat every N chunks | Chain dies silently during slow streams | Heartbeat on a wall-clock timer (30s default) |
| `await stream.close()` after kill | Half-written chunks can leak to the caller | Wrap the stream in `try/finally`, always close |
| Catching `Exception` instead of `BaseException` around the loop | Kill signal is swallowed, agent keeps running | Catch `WorkflowKilledInterrupt` explicitly first |
| Forgetting `track_llm()` after a manual stream | Dashboard shows zero cost, budget never decremented | Always report final usage, even via estimation |

## See also

- [Chain context → soft mode](../concepts/workflow.md#chain-context)
- [Errors → kill contract](../reference/errors.md#sdk-exception-hierarchy-python)
- [Use with FastAPI](../how-to/fastapi.md) — streaming inside ASGI handlers
