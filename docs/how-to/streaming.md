# Stream LLM responses

The SDK tracks streaming responses correctly — every chunk is
forwarded to your caller in real time, and the cost is reported from
the final chunk (which carries the `usage` block).

## The pattern

```python title="streaming_agent.py"
import time
import nullrun
from openai import AsyncOpenAI
from nullrun import init_or_die, chain, protect, shutdown

init_or_die()
client = AsyncOpenAI()


@protect
async def stream_answer(prompt: str):
    # The @protect gate runs once at the start of the call.
    # Cost is unknown at that point — the gate approves against
    # the budget cap using the projected cost from policy.
    stream = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        stream=True,
    )
    async for chunk in stream:
        yield chunk.choices[0].delta.content or ""
```

That's the streaming path. The transport hook buffers chunks
internally so the final `usage` block is read before the SDK emits
`/track` — your user sees chunks in real time, but the cost is
accurate.

## Long streams: keep the chain alive

A long stream that exceeds the chain idle TTL (300s by default) will
be killed mid-chunk. To keep it alive, the SDK's background WS
listener sends a heartbeat automatically **as long as the connection
is alive and the policy allows it**. For most streams you do
nothing.

For very long streams (multi-minute responses with soft mode), use a
`chain` context — the SDK extends the chain TTL while the call is
in-flight and the gate is held open:

```python title="streaming_with_chain.py"
import nullrun
from openai import OpenAI
from nullrun import init_or_die, chain, protect, shutdown

init_or_die()
client = OpenAI()


@protect
def long_stream(prompt: str):
    # `chain` opens a soft-mode gate and keeps it alive for the
    # duration of the call. While inside the block, the SDK
    # automatically extends the chain TTL as long as the WebSocket
    # connection is up.
    with chain("my-long-stream", op="start"):
        stream = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )
        for chunk in stream:
            yield chunk.choices[0].delta.content or ""
```

!!! warning "Heartbeat is automatic — do not roll your own"
    The SDK's WS push listener sends a heartbeat at the chain
    cadence. Rolling your own heartbeat (e.g. every N chunks) is
    **wrong** — a slow stream that produces 5 chunks in 5 minutes
    will look "healthy" by chunk count but the chain will still die
    from idle timeout. The cadence is wall-clock based (30s
    default), not chunk-count based.

## Soft mode for streams

If your stream is long enough that budget is a concern, use soft
mode:

```python title="streaming_soft_mode.py"
import nullrun
from openai import OpenAI
from nullrun import init_or_die, chain, protect, shutdown

init_or_die()
client = OpenAI()


@protect
def stream_with_overdraft(prompt: str):
    with chain("research-stream", op="start"):
        stream = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )
        for chunk in stream:
            yield chunk.choices[0].delta.content or ""
```

The policy must have `enforcement_mode = "Soft"` for the overdraft to
apply. Without it, the stream hard-blocks the moment projected cost
exceeds budget. See [Chain context](../concepts/workflow.md#chain-context-soft-mode-budget-gate)
for the full mechanics.

## Kill signal mid-stream

If an operator hits **Kill** while your stream is mid-flight, the
SDK raises `WorkflowKilledInterrupt` at the next `yield` boundary:

```python title="streaming_kill_safe.py"
from nullrun.breaker.exceptions import WorkflowKilledInterrupt

@protect
async def stream_kill_safe(prompt: str):
    stream = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        stream=True,
    )
    try:
        async for chunk in stream:
            yield chunk.choices[0].delta.content or ""
    except WorkflowKilledInterrupt:
        # Stream is cancelled at this yield. Clean up and re-raise
        # so the kill contract reaches the top of your agent loop.
        await stream.close()
        raise
```

`WorkflowKilledInterrupt` is a `BaseException` — catch it **before**
any `except Exception` block in your code, otherwise you'll swallow
the kill.

## Tracking without auto-instrumentation

If the SDK's httpx transport hook can't see your custom streaming
client (e.g. you're using a vendor-specific SDK that bypasses httpx),
call `track_llm` manually after the stream ends:

```python title="manual_stream_track.py"
import nullrun
from openai import OpenAI
from nullrun import init_or_die, protect, shutdown, track_llm

init_or_die()
client = OpenAI()


@protect
def custom_stream(prompt: str):
    stream = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        stream=True,
    )

    chunks = []
    for chunk in stream:
        text = chunk.choices[0].delta.content or ""
        chunks.append(text)
        yield text

    # Manually report usage after the stream finishes.
    # OpenAI's `stream_options={"include_usage": True}` puts a usage
    # block on the final chunk; otherwise you have to estimate.
    # See https://platform.openai.com/docs/api-reference/chat-streaming
    stream = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        stream=True,
        stream_options={"include_usage": True},
    )
    final = None
    for chunk in stream:
        text = chunk.choices[0].delta.content or ""
        final = chunk
        yield text
    if final and getattr(final, "usage", None):
        track_llm(
            input_tokens=final.usage.prompt_tokens,
            output_tokens=final.usage.completion_tokens,
            model="gpt-4o-mini",
        )
```

Without `track_llm()` the SDK has no usage to report — the budget
counter is never credited and the next `/gate` may reject the next
call based on stale spend.

> **Note:** the auto-instrumentation httpx hook handles usage
> extraction for the standard `openai` SDK without any extra code.
> The manual path above is only needed when you've replaced the
> OpenAI client with a custom one.

## Common pitfalls

| Pitfall | Symptom | Fix |
|---|---|---|
| Heartbeat every N chunks | Chain dies silently during slow streams | Heartbeat on a wall-clock timer (30s default) |
| `await stream.close()` after kill | Half-written chunks can leak to the caller | Wrap the stream in `try/finally`, always close |
| Catching `Exception` instead of `BaseException` around the loop | Kill signal is swallowed, agent keeps running | Catch `WorkflowKilledInterrupt` explicitly first |
| Forgetting `track_llm()` after a manual stream | Dashboard shows zero cost, budget never decremented | Always report final usage, even via estimation |

## See also

- [Chain context → soft mode](../concepts/workflow.md#chain-context-soft-mode-budget-gate)
- [Errors → kill contract](../reference/errors.md#sdk-exception-hierarchy-python)
- [Use with FastAPI](../how-to/fastapi.md) — streaming inside ASGI
  handlers
