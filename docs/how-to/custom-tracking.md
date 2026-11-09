---
title: Manual cost and event tracking
description: Report LLM cost, tool calls, and business events by hand with the runtime tracking methods, and pair every report with a budget check.
maturity: stable
---

# Manual cost and event tracking

Auto-instrumentation books most LLM calls for you. The SDK watches the
HTTP client and the framework hooks, reads the token counts out of the
provider response, and reports them.

Reach for the runtime's tracking methods when the SDK cannot see the
call:

- your LLM client does not use `httpx`, for example a raw socket client
  or an offline batch job reading cached completions;
- you proxy the call, so the SDK reads your proxy's response instead of
  the provider's;
- you call something that is not an HTTP request, such as a database
  query or a custom side-effecting function;
- you want a business event in the record, such as a milestone or a
  variant assignment.

If your client is the standard OpenAI, Anthropic, Gemini, Cohere,
Mistral, or Bedrock SDK, do not report the call by hand.
Auto-instrumentation already fires, and a second report double-counts
the tokens.

## The three methods

They live on the runtime instance. Reach the runtime with
`nullrun.get_runtime()`.

There is no package-level `nullrun.track_llm`, `nullrun.track_tool`, or
`nullrun.track`. Those names do not exist. The public package surface is
the `@protect` decorator plus the lifecycle and error helpers. See
[SDK API → Package surface](../reference/sdk-api.md#package-surface).

| Method | Purpose | Required fields |
|---|---|---|
| `runtime.track_llm(input_tokens, output_tokens=0, *, model=None, latency_ms=None, metadata=None)` | Report an LLM call | `input_tokens`; `model` required |
| `runtime.track_tool(tool_name, duration_ms=None, *, is_retry=False, metadata=None)` | Report a tool call | `tool_name` |
| `runtime.track(event)` | Report an arbitrary event | `type` |

`runtime.track_event(event_type, **kwargs)` is the same thing with the
event type as the first argument.

## An LLM report needs a reservation

The gateway books a cost against a reservation. The SDK drops an
`llm_call` event that has no reservation in scope, and logs a warning
that names the event type and the workflow. Nothing is billed.

Two ways to get a reservation:

| Way | What it does |
|---|---|
| Wrap the call in `@protect` | Runs the budget check and the tool policy, then hands the body a reservation |
| Call `runtime.check_workflow_budget()` first | Runs the budget check only |

A call the SDK cannot see therefore costs nothing until you report it
inside one of those two scopes. Report it outside them and the spend
total stays too low, so the cap fires late.

## Example

```python title="track_custom.py"
import nullrun
from nullrun import protect


@protect
def run_step(response, elapsed_ms: int):
    runtime = nullrun.get_runtime()
    runtime.track_llm(
        input_tokens=response.usage.prompt_tokens,
        output_tokens=response.usage.completion_tokens,
        model="custom-llm-v1",
        latency_ms=elapsed_ms,
        metadata={"vendor": "internal"},
    )
    runtime.track_event("agent.milestone", step="research_complete")
```

`@protect` reports the tool call itself, under the function name. Call
`runtime.track_tool` only for a tool the SDK cannot see.

`@protect` uses the function name as the tool name. Name the function
after the tool the policy matches:

```python title="gated_tool.py"
from nullrun import protect


@protect
def send_email(to: str, body: str) -> None:
    ...
```

A tool call that never passes through `@protect` is never checked
against a blocked-tool rule. The manual report never blocks it either.

## Tracking is reporting, not enforcement

`track_tool` records the call. It does not run the tool policy.

The policy engine runs on the gate, which `@protect` triggers.

## Caveats

- **The model name is required.** The gateway prices the call from the
  model name and the token counts. An `llm_call` event with no `model`
  field is tagged by the SDK, and the gateway refuses the report with
  `422`.
- **Buffering.** LLM events go to the gateway one at a time. Tool events
  and span events go out in batches, flushed on a timer or when the
  batch fills. `init()` registers a shutdown hook that drains the
  buffer, so a clean process exit never loses events.
- **Dedupe covers `track_event` only.** The SDK gives a `track_event` a
  content fingerprint and drops a repeat of the same event.
  `track_llm` and `track_tool` carry no fingerprint, so two calls with
  the same payload are two events.
- **Control-plane checks.** A tracking call reads the workflow state. A
  paused or killed workflow raises out of `track_llm` as well as out of
  `@protect`.

## See also

- [SDK API → Manual tracking](../reference/sdk-api.md#manual-tracking)
- [LLM frameworks](llm-frameworks.md) — which providers the SDK sees on
  its own
