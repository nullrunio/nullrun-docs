# Manual cost / event tracking

Most of the time auto-instrumentation handles cost tracking — the
httpx transport hook reads `usage` from OpenAI / Anthropic / Gemini /
Cohere responses and emits `track_llm` automatically. But there are
cases where you need to track manually.

## When to track manually

Use `track_llm`, `track_tool`, and `track_event` when any of these
is true:

- **Your LLM client bypasses httpx** — Bedrock via boto3, Cohere on a
  raw socket, an offline batch job reading cached completions.
- **You proxy the LLM call** — your service sits between the agent
  and the upstream provider, and the auto-instrumentation hook sees
  your proxy's response (zero usage) instead of the upstream's.
- **You call a tool that isn't an HTTP call** — a database query, a
  state-machine transition, a custom function with side effects you
  want in the decision log.
- **You have a custom business event** — milestone reached, retry
  attempt, A/B test variant assigned. These aren't LLM or tool
  calls but you want them in the same audit trail.

If your SDK wraps the standard OpenAI / Anthropic / Gemini / Cohere
clients, do **not** call `track_llm` manually — the auto-instrumentation
will fire and you'll double-count.

## `track_llm` — manual LLM cost

```python title="track_llm_custom.py"
import nullrun
from nullrun import track_llm

# After your custom LLM call returns:
track_llm(
    input_tokens=response.usage.prompt_tokens,
    output_tokens=response.usage.completion_tokens,
    model="custom-llm-v1",
    latency_ms=response.elapsed_ms,
    metadata={
        "vendor": "internal",
        "deployment": "us-east-1",
        "trace_id": "abc-123",
    },
)
```

| Field | Required | Notes |
|---|---|---|
| `input_tokens` | yes | Prompt / context tokens consumed |
| `output_tokens` | yes | Completion tokens generated |
| `model` | recommended | Pricing lookup key — must match an entry in your `model_pricing` table |
| `latency_ms` | optional | End-to-end latency for the call |
| `metadata` | optional | Free-form dict stored on the event |

Without `track_llm`, the budget counter is never credited for this
call — the next `/gate` may reject based on stale spend.

## `track_tool` — manual tool cost

```python title="track_tool_custom.py"
from nullrun import track_tool

# After a tool call completes (regardless of success/failure):
track_tool(
    tool_name="send_email",
    duration_ms=240,
    is_retry=False,
    metadata={"to": "user@example.com", "template_id": "weekly-digest"},
)
```

The `tool_name` flows through to the policy engine — a `ToolBlock`
policy with pattern `send_*` will catch a manual call to
`track_tool("send_email", ...)`. Use the same tool names you would
pass to auto-instrumentation so policy enforcement stays consistent.

## `track_event` — arbitrary observability

```python title="track_event_custom.py"
from nullrun import track_event

track_event(
    "agent.milestone",
    step="research_complete",
    elapsed_secs=42,
    subagent="research-node",
)
track_event(
    "agent.error",
    code="validation_failed",
    field="email",
)
```

`event_type` becomes a category you can filter the decision log by.
Everything else becomes searchable metadata on the event row.

## When the SDK can't see the call

If your tool isn't called from inside `@protect`, you can wrap the
manual tracking in `@protect` so the gate still runs:

```python title="track_outside_protect.py"
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

This way the gate enforces the budget cap **before** the call, and
the manual `track_llm` reconciles the actual spend afterwards — the
same two-phase pattern auto-instrumentation uses.

## Caveats

- **Buffering**: `track_*` events don't go straight to the gateway.
  They buffer in the runtime's event batch and flush on the next
  `@protect` call or `flush_interval_ms`. If your process exits
  before the flush, the events are lost — call `shutdown(flush=True)`
  in your `finally` block.
- **Order**: `track_*` events arrive at the gateway in submission
  order, but the SDK's internal dedup LRU can collapse duplicate
  sibling emissions from auto-instrumentation. Manual `track_*`
  calls are never deduped.
- **Idempotency**: each `track_*` call gets a fresh UUID. Calling it
  twice with the same payload produces two events. For retries, gate
  the call yourself.

## See also

- [SDK API → track_llm / track_tool / track_event](../reference/sdk-api.md#track_llm-manual-usage)
- [Use with Bedrock](../how-to/bedrock.md) — example of a non-httpx
  vendor that uses manual tracking
- [Errors → what goes through the decision log](../reference/errors.md)
