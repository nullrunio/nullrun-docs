---
title: Custom Tracking
description: Manually report cost and events with runtime.track_llm, runtime.track_tool, and runtime.track when auto-instrumentation doesn't fit your runtime.
---

# Manual cost / event tracking

Most of the time auto-instrumentation handles cost tracking — the
httpx transport hook reads `usage` from OpenAI / Anthropic / Gemini /
Cohere responses and emits `track_llm` automatically. Reach for the
runtime's `track_llm` / `track_tool` / `track` methods manually when:

- your LLM client bypasses httpx (Bedrock via boto3, Cohere on a raw
  socket, an offline batch reading cached completions);
- you proxy the LLM call and the auto-instrumentation hook sees your
  proxy's response (zero usage) instead of the upstream's;
- you call a tool that isn't an HTTP call (database query, state
  transition, side-effect-bearing custom function);
- you have a custom business event (milestone, retry attempt, A/B
  variant) that you want in the decision log.

If your SDK wraps the standard OpenAI / Anthropic / Gemini / Cohere
clients, do **not** call `track_llm` manually — auto-instrumentation
will fire and you'll double-count.

The three trackers live on the runtime instance — reach them via
`nullrun.get_runtime()`. They are not exposed as top-level names on
the `nullrun` package; the curated public surface is the universal
`@protect` decorator plus lifecycle / error helpers.

## The three trackers

| API | Purpose | Required fields |
| --- | --- | --- |
| `runtime.track_llm(input_tokens, output_tokens, *, model=None, latency_ms=None, metadata=None)` | Manual LLM cost | `input_tokens`, `output_tokens`; `model` recommended |
| `runtime.track_tool(tool_name, duration_ms=None, *, is_retry=False, metadata=None)` | Manual tool cost | `tool_name` (must match `ToolBlock` patterns) |
| `runtime.track({"type": ..., ...})` | Arbitrary observability | `type` (becomes a filterable event category) |

Without `track_llm` the budget counter is never credited for the
call — the next `/gate` may reject based on stale spend.

## Example

```python title="track_custom.py"
import nullrun

runtime = nullrun.get_runtime()

# After your custom LLM call returns:
runtime.track_llm(
    input_tokens=response.usage.prompt_tokens,
    output_tokens=response.usage.completion_tokens,
    model="custom-llm-v1",
    latency_ms=response.elapsed_ms,
    metadata={"vendor": "internal", "trace_id": "abc-123"},
)

# After a tool call (regardless of success/failure):
runtime.track_tool(
    tool_name="send_email",
    duration_ms=240,
    is_retry=False,
    metadata={"to": "user@example.com"},
)

# Arbitrary business events:
runtime.track({"type": "agent.milestone", "step": "research_complete", "elapsed_secs": 42})
runtime.track({"type": "agent.error", "code": "validation_failed", "field": "email"})
```

`track_tool`'s `tool_name` flows through to the policy engine — a
`ToolBlock` policy with pattern `send_*` catches a manual call to
`runtime.track_tool("send_email", ...)`. Use the same tool names you
would pass to auto-instrumentation so policy enforcement stays
consistent.

## When the SDK can't see the call

If your tool isn't called from inside `@protect`, wrap the manual
tracking in `@protect` so the gate still runs:

```python
import nullrun
from nullrun import protect

runtime = nullrun.get_runtime()

@protect
def call_custom_llm(prompt):
    response = my_custom_client.complete(prompt)
    runtime.track_llm(
        input_tokens=response.usage.input,
        output_tokens=response.usage.output,
        model="custom-llm-v1",
    )
    return response.text
```

## Caveats

- **Buffering**: `track_*` events don't go straight to the gateway —
  they buffer in the runtime's event batch and flush on the next
  `@protect` call or `flush_interval_ms`. `init()` auto-registers
  `nullrun.shutdown(flush=True)` via `atexit`, so a clean process
  exit always drains the buffer; an explicit `finally` block only
  matters for early teardown.
- **Idempotency**: each `track_*` call gets a fresh UUID. Calling it
  twice with the same payload produces two events. For retries, gate
  the call yourself.

## See also

- [SDK API → runtime.track_llm / track_tool / track](../reference/sdk-api.md#runtimetrack_llm-manual-usage)
- [LLM frameworks](../how-to/llm-frameworks.md) — non-httpx vendors
  (Bedrock, Cohere) that use manual tracking