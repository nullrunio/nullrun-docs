# Manual cost / event tracking

Most of the time auto-instrumentation handles cost tracking — the
httpx transport hook reads `usage` from OpenAI / Anthropic / Gemini /
Cohere responses and emits `track_llm` automatically. Use
`track_llm`, `track_tool`, and `track_event` manually when:

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

## The three trackers

| API | Purpose | Required fields |
| --- | --- | --- |
| `track_llm(input_tokens, output_tokens, model, ...)` | Manual LLM cost | `input_tokens`, `output_tokens`; `model` recommended |
| `track_tool(tool_name, duration_ms, ...)` | Manual tool cost | `tool_name` (must match `ToolBlock` patterns) |
| `track_event(event_type, ...)` | Arbitrary observability | `event_type` (becomes a filterable category) |

Without `track_llm` the budget counter is never credited for the
call — the next `/gate` may reject based on stale spend.

## Example

```python title="track_custom.py"
import nullrun
from nullrun import track_llm, track_tool, track_event

# After your custom LLM call returns:
track_llm(
    input_tokens=response.usage.prompt_tokens,
    output_tokens=response.usage.completion_tokens,
    model="custom-llm-v1",
    latency_ms=response.elapsed_ms,
    metadata={"vendor": "internal", "trace_id": "abc-123"},
)

# After a tool call (regardless of success/failure):
track_tool(
    tool_name="send_email",
    duration_ms=240,
    is_retry=False,
    metadata={"to": "user@example.com"},
)

# Arbitrary business events:
track_event("agent.milestone", step="research_complete", elapsed_secs=42)
track_event("agent.error", code="validation_failed", field="email")
```

`track_tool`'s `tool_name` flows through the policy engine — a
`ToolBlock` policy with pattern `send_*` catches a manual call to
`track_tool("send_email", ...)`. Use the same tool names you would
pass to auto-instrumentation so policy enforcement stays consistent.

## When the SDK can't see the call

If your tool isn't called from inside `@protect`, wrap the manual
tracking in `@protect` so the gate still runs:

```python
from nullrun import protect, track_llm

@protect
def call_custom_llm(prompt):
    response = my_custom_client.complete(prompt)
    track_llm(
        input_tokens=response.usage.input,
        output_tokens=response.usage.output,
        model="custom-llm-v1",
    )
    return response.text
```

## Caveats

- **Buffering**: `track_*` events don't go straight to the gateway —
  they buffer in the runtime's event batch and flush on the next
  `@protect` call or `flush_interval_ms`. If your process exits
  before the flush, the events are lost; call
  `shutdown(flush=True)` in your `finally` block.
- **Idempotency**: each `track_*` call gets a fresh UUID. Calling it
  twice with the same payload produces two events. For retries, gate
  the call yourself.

## See also

- [SDK API → track_llm / track_tool / track_event](../reference/sdk-api.md#track_llm-manual-usage)
- [Use with Bedrock](../how-to/bedrock.md) — non-httpx vendor that
  uses manual tracking
