---
title: SDK API
maturity: stable
description: Reference for the NullRun Python SDK: the public package surface, the protect decorator, context managers, manual tracking, runtime methods, and the full exception catalog with error codes.
---

# SDK API

The Python SDK lives in
[`nullrunio/nullrun-sdk-python`](https://github.com/nullrunio/nullrun-sdk-python).
Package name on PyPI: **`nullrun`**.

```bash title="shell"
pip install nullrun                    # core — covers every LLM SDK that uses httpx
pip install nullrun[opentelemetry]     # OTel span/metric export on top of the core
pip install nullrun[dev]               # pytest + respx + mypy + ruff + coverage
```

Auto-instrumentation for httpx-based libraries (`openai`,
`anthropic`, `openai-agents`, …) attaches lazily on the first
`@protect` call — see [Auto-instrumentation](../getting-started/install.md#what-gets-instrumented).

## Package surface

`dir(nullrun)` returns **only the curated `__all__` list** — 46 names.
Everything else the SDK exposes is imported on first attribute access, so it
never shows up in `dir()` or in tab-completion until you touch it.

```python title="public_surface.py"
from nullrun import init, protect, workflow, span, agent, chain
```

### Curated surface (`__all__`, shown by `dir(nullrun)`)

| Symbol | Kind | Purpose |
|---|---|---|
| `__version__` | value | SDK version string. |
| `init` | function | Create the runtime eagerly. |
| `protect` | decorator | Gate a function. The only entry point for enforcement. |
| `shutdown` | function | Close the runtime and drain buffered events. |
| `on_error` | function | Register a global error hook. |
| `guard` | context manager | Turn an SDK error into a clean process exit. |
| `format_user_message` | function | Render an exception as end-user-facing text. |
| `set_user_message` | function | Override the message for one `error_code`. |
| `NullRunError` | exception | Base class for every SDK exception. |
| `NullRunDecision` | exception | Marker for expected policy outcomes. |
| `NullRunInfrastructureError` | exception | Marker for system failures. |
| `NullRunDeniedError` | exception | Operator refused this specific call. |
| `NullRunBudgetError` | exception | Budget exhausted. |
| `NullRunBudgetRecheckFailedError` | exception | Budget moved between gate and execute. |
| `NullRunToolBlockedError` | exception | Tool is in the block list. |
| `NullRunChainError` | exception | Chain-scope check failed. |
| `NullRunConsumeOverbudgetError` | exception | Actual cost exceeded the reservation. |
| `NullRunWorkflowInactiveError` | exception | Workflow is inactive. |
| `WorkflowKilledInterrupt` | exception | Operator kill signal. |
| `NullRunWorkflowKilledError` | exception | Typed name for the kill signal. |
| `NullRunApprovalNotYetApprovedError` | exception | Approval still pending. |
| `NullRunApprovalResponseMissingError` | exception | No approval row for the call. |
| `NullRunApprovalDeniedError` | exception | Operator denied the approval. |
| `NullRunApprovalExpiredError` | exception | Approval expired. |
| `NullRunApprovalReplayRejectedError` | exception | Approval already consumed. |
| `NullRunApprovalDigestMismatchError` | exception | Action digest drifted. |
| `NullRunApprovalToolDigestMismatchError` | exception | Tool digest drifted. |
| `NullRunApprovalToolMismatchError` | exception | Tool outside the approved set. |
| `NullRunApprovalDbUnavailableError` | exception | Approval store unreachable. |
| `NullRunMcpDestructiveBlockedError` | exception | Destructive MCP tool blocked. |
| `NullRunMcpReadonlyBypassBlockedError` | exception | Read-only MCP tool blocked. |
| `NullRunMcpApprovalRequiredError` | exception | MCP tool needs operator approval. |
| `NullRunProtocolError` | exception | Wire-protocol version mismatch. |
| `NullRunMalformedGateResponseError` | exception | Gate response is not a decision. |
| `NullRunGateIndeterminateError` | exception | Decision could not be determined. |
| `NullRunUnknownActionError` | exception | Control-plane action type unknown. |
| `NullRunUnclassifiedRefusalError` | exception | Refusal category not understood. |
| `NullRunTransportError` | exception | Transport failure. |
| `NullRunBackendError` | exception | Gateway returned 5xx. |
| `NullRunExecutionNotFoundError` | exception | Execution id unknown or expired. |
| `RateLimitError` | exception | Gateway returned 429. |
| `NullRunRateLimitRedisError` | exception | Rate limiter unavailable. |
| `NullRunAuthError` | exception | API key rejected. |
| `NullRunConfigError` | exception | Misconfiguration. |
| `BreakerTransportError` | exception | Events could not be delivered. |
| `InsecureTransportError` | exception | HTTPS required. |

### Lazy surface

These names import fine (`from nullrun import X`) but stay out of `dir(nullrun)`.

| Group | Names |
|---|---|
| Runtime | `NullRunRuntime`, `get_runtime`, `get_protected_runtime`, `reset` |
| Context managers | `workflow`, `span`, `agent`, `chain` |
| Context getters | `get_workflow_id`, `get_trace_id`, `get_span_id`, `get_agent_id`, `get_call_model`, `get_call_tools`, `get_chain_id`, `get_chain_op` |
| Context setters | `set_call_context`, `set_chain_id`, `set_chain_op` |
| Tracing | `SpanContext`, `get_current_span`, `create_root_span`, `create_child_span`, `set_span`, `reset_span` |
| Actions | `ActionHandler`, `ActionType`, `ActionEvent`, `WebhookConfig`, `handle_action`, `register_action_handler`, `get_action_handler` |
| Exceptions | `BreakerError`, `NullRunBlockedException`, `NullRunAuthenticationError`, `WorkflowPausedException`, `TransportErrorSource` |
| Status | `NullRunStatus`, `RecentError`, `WorkflowState`, `ErrorContext` |
| Audit | `AuditEntry`, `AuditLogMeta`, `AuditLogPage`, `AuditQuery`, `AuditVerifyResult`, `AuditExportJob`, `AuditExportStatus` |
| Messages | `get_user_message` |

## Lifecycle

### `init`

```python title="init.py"
import nullrun

nullrun.init(api_key="nr_live_...", api_url="https://api.nullrun.io")
```

| Parameter | Default | Behaviour |
|---|---|---|
| `api_key` | `NULLRUN_API_KEY` | Required. A whitespace-only value is rejected. A missing key raises `NullRunAuthenticationError` with `error_code="NR-C001"`. |
| `api_url` | `NULLRUN_API_URL`, else `https://api.nullrun.io` | Gateway base URL. |
| `debug` | `False` | Turns on debug logging. |
| `fail_on_exit` | `False` | On a missing key, print the developer report to stderr and `sys.exit(1)` instead of raising. |
| `on_denied` | `"raise"` | `"raise"` or `"message"`. `"message"` makes the operator's refusal surface as `NullRunDeniedError`, whose `agent_message` is text the gateway marks safe to show a model. Any other value raises `ValueError`. The flag applies to a `denied` refusal only. |

`init()` is optional. The first `@protect` call creates the runtime lazily from
`NULLRUN_API_KEY`.

`init()` also registers `nullrun.shutdown()` with `atexit`, probes
`/api/v1/capabilities` for the protocol version, and installs
auto-instrumentation.

### `protect`

```python title="protect.py"
import nullrun

@nullrun.protect
def send_email(to: str, body: str) -> None:
    ...
```

`protect(fn=None)` takes no keyword arguments. Both forms work:

```python
import nullrun

@nullrun.protect
def call(): ...

@nullrun.protect()
def call(): ...
```

It works on sync and async functions. Every protected call routes through the
gateway, which answers with one of five decisions: `allow`, `block`,
`require_approval`, `soft_pass`, or `deny`.

### `shutdown`

```python title="shutdown.py"
nullrun.shutdown(timeout=2.0, flush=True)
```

`timeout` is reserved and unused today. `flush=False` skips the final network
call and cancels the flush thread. The call is safe and idempotent, and it is a
no-op when `init()` never ran.

### `on_error`

```python title="on_error.py"
import nullrun

def report(err, ctx):
    print(err.error_code, ctx.stage)

unregister = nullrun.on_error(report)
```

The hook takes `(NullRunError, ErrorContext)` and must be synchronous. It runs
first, then the exception propagates. Hook exceptions are caught and logged at
debug level, so a misbehaving hook cannot break the SDK. The returned callable
unregisters the hook and is idempotent.

### `guard`

```python title="guard.py"
import nullrun

with nullrun.guard(exit_code=1):
    run_my_agent("hello")
```

`guard(*, exit_code=1)` is a context manager. It catches every `NullRunError`
raised inside the block, prints a structured developer report to stderr, and
calls `sys.exit(exit_code)`. The kill signal propagates unchanged so it reaches
the top of the agent loop.

### Messages

```python title="messages.py"
import nullrun

text = nullrun.format_user_message(exc)
nullrun.set_user_message("NR-B004", "You've used all your support credits.")
raw = nullrun.get_user_message("NR-B004")
```

`format_user_message(exc)` renders an exception as end-user-facing text. Use it
in place of `str(exc)` whenever a person reads the message — `str(exc)` carries
internal identifiers.

`set_user_message(code, text)` overrides the message for one `error_code` for
the lifetime of the process. Pass `text=""` to clear the override.
`get_user_message(code)` returns the override when one is set, the catalog
default otherwise.

## Context managers

| Manager | Yields | Behaviour |
|---|---|---|
| `workflow(name=None)` | `workflow_id` | Sets the workflow id for every event inside the block. The id is `name` or a fresh UUID. Also mints a root trace and span. |
| `span(name=None)` | `span_id` | Sets the active span for nested traces. |
| `agent(name=None)` | `agent_id` | Sets the agent identity for events inside the block. |
| `chain(chain_id, op="start")` | `chain_id` | Scopes the calls to one chain. `op` must be `"start"`, `"continue"`, `"end"`, or `"auto"`; any other value raises `ValueError`. `chain_id` must be a **UUID v4**; any other format raises `ValueError`. |

```python title="chain.py"
import uuid
import nullrun

chain_id = str(uuid.uuid4())
with nullrun.chain(chain_id, op="start") as cid:
    agent.run_long_loop()
```

`chain()` does not close the chain on exit. Close it explicitly with
`runtime.chain_end(chain_id)`.

### `set_call_context`

```python title="set_call_context.py"
import nullrun

nullrun.set_call_context(
    model="claude-sonnet-4-6",
    tools=["search", "send_email"],
    max_output_tokens=4096,
)
```

`set_call_context(model=None, tools=None, max_output_tokens=None)` attaches
per-call context that the gateway uses when it evaluates the call. Pass `None`
to leave a field unchanged. `max_output_tokens` is sent only when it is a
positive integer.

Manual setters `set_chain_id(chain_id)` and `set_chain_op(op)` set the chain
scope directly. Each returns a token.

## Manual tracking

Tracking methods live on the runtime, not on the package. Reach the runtime
with `nullrun.get_runtime()`.

| Method | Signature |
|---|---|
| `track_llm` | `track_llm(input_tokens, output_tokens=0, *, model=None, latency_ms=None, metadata=None)` |
| `track_tool` | `track_tool(tool_name, duration_ms=None, *, is_retry=False, metadata=None)` |
| `track` | `track(event: dict)` |
| `track_event` | `track_event(event_type, **kwargs)` |

```python title="track_llm.py"
import nullrun

runtime = nullrun.get_runtime()
runtime.track_llm(
    input_tokens=response.usage.prompt_tokens,
    output_tokens=response.usage.completion_tokens,
    model="custom-model-v1",
    latency_ms=response.elapsed_ms,
)
```

```python title="track_tool.py"
import nullrun

nullrun.get_runtime().track_tool(
    tool_name="send_email",
    duration_ms=240,
    is_retry=False,
)
```

```python title="track.py"
import nullrun

nullrun.get_runtime().track({
    "type": "agent.milestone",
    "step": "research_complete",
    "elapsed_secs": 42,
})
```

```python title="track_event.py"
import nullrun

nullrun.get_runtime().track_event("workflow_start", workflow_id="wf-123")
```

`track_llm` reports token counts. The gateway computes cost from the tokens and
the org's pricing. A call the SDK cannot see is never billed, and the next
budget check can reject against a stale spend.

`track_tool` reports a tool call by name. The name reaches the policy engine,
so a blocked-tool policy can catch a manual call.

`track` takes an arbitrary event payload. The `type` field becomes the
filterable event category. `track_event` is the same thing with the event type
as its first argument.

## Runtime methods

| Method | Purpose |
|---|---|
| `status()` | Snapshot of the runtime. |
| `check_workflow_budget(*, model=None, estimated_tokens=None, max_output_tokens=None)` | Ask whether the workflow has budget left. |
| `execute(tool_name, input_data, mode="auto", ...)` | Run one tool call through the gateway. |
| `heartbeat(chain_id)` | Post a cadence heartbeat for a chain. |
| `ping_chain(chain_id, interval=30.0)` | Keep a chain alive on a timer. |
| `cancel_execution(execution_id, reason=None)` | Cancel an in-flight execution. |
| `consume_approval(...)` | Close an approved grant. |
| `chain_end(chain_id)` | Close a chain. |
| `approximate_budget()` | Best-effort budget view for display. |
| `audit` | Audit log reader: `.list()`, `.verify()`, `.list_exports()`, `.create_export()`, `.export_status()`. |
| `shutdown(flush=True)` | Close the runtime. |

### `status()`

```python title="status.py"
import nullrun

snapshot = nullrun.get_runtime().status()
print(snapshot.state)
```

`status()` returns a frozen `NullRunStatus` dataclass. It is safe to call from
any thread.

| Field | Meaning |
|---|---|
| `state` | `ok`, `degraded`, `offline`, or `misconfigured`. |
| `api_key_valid` | `True`, `False`, or `None` when never tested. |
| `api_key_prefix` | A fingerprint of the API key. Carries no character of the key. |
| `organization_id` | The org the key belongs to. |
| `workflow_id` | The bound workflow, or `None`. |
| `api_url` | The gateway base URL. |
| `backend_reachable` | `True`, `False`, or `None` when never tested. |
| `ws_connected` | `True`, `False`, or `None` when not started. |
| `workflow_state` | The remote workflow state, or `None`. |
| `recent_errors` | Bounded list of recent errors. |

There is no top-level `nullrun.status()`.

## Exceptions

Every public SDK exception inherits from `NullRunError` and carries four
structured fields: `error_code` (machine-readable, e.g. `"NR-B004"`),
`user_action` (imperative hint), `retryable` (bool), and `docs_url`.

`NullRunDecision` and `NullRunInfrastructureError` are marker classes. They let
host code catch every expected policy outcome with one clause, and every system
failure with another.

`NullRunBlockedException` carries `.workflow_id`, `.reason`, `.action`,
`.tool_name`, `.status_code`, and `.details`. It has **no** `.message`
attribute — use `str(exc)`.

| Class | Base | `error_code` | Raised when |
|---|---|---|---|
| `NullRunError` | `BreakerError` | `NR-0000` | Base class for every SDK exception. |
| `NullRunDecision` | `NullRunError` | `NR-0000` | Marker for expected policy outcomes. |
| `NullRunInfrastructureError` | `NullRunError` | `NR-0000` | Marker for system failures. |
| `NullRunBlockedException` | `NullRunDecision` | `NR-X001` | Generic policy block. |
| `NullRunDeniedError` | `NullRunBlockedException` | `NR-D001` | The operator refused this specific call. Carries `.agent_message`. |
| `NullRunBudgetError` | `NullRunBlockedException` | `NR-B004` | Budget exhausted. |
| `NullRunBudgetRecheckFailedError` | `NullRunBudgetError` | `NR-B006` | The budget moved between the gate call and the execute call. |
| `NullRunToolBlockedError` | `NullRunBlockedException` | `NR-T001` | The tool is in the block list. |
| `NullRunApprovalDbUnavailableError` | `NullRunBlockedException` | `NR-A016` | The approval store is unreachable. |
| `NullRunApprovalResponseMissingError` | `NullRunBlockedException` | `NR-A004` | The gate asked for approval and no approval row exists. |
| `NullRunApprovalNotYetApprovedError` | `NullRunBlockedException` | `NR-A010` | The operator has not decided yet. |
| `NullRunApprovalDeniedError` | `NullRunBlockedException` | `NR-A011` | The operator denied the approval. |
| `NullRunApprovalExpiredError` | `NullRunBlockedException` | `NR-A012` | The approval expired. |
| `NullRunApprovalReplayRejectedError` | `NullRunBlockedException` | `NR-A015` | The grant was already consumed. |
| `NullRunApprovalDigestMismatchError` | `NullRunBlockedException` | `NR-A013` | The action changed since the approval. |
| `NullRunApprovalToolDigestMismatchError` | `NullRunBlockedException` | `NR-A014` | The tool surface changed since the approval. |
| `NullRunApprovalToolMismatchError` | `NullRunBlockedException` | `NR-A017` | The tool is outside the approved tool set. |
| `NullRunMcpDestructiveBlockedError` | `NullRunBlockedException` | `NR-MCP01` | A destructive MCP tool was blocked. |
| `NullRunMcpReadonlyBypassBlockedError` | `NullRunBlockedException` | `NR-MCP02` | A read-only MCP tool was blocked. |
| `NullRunMcpApprovalRequiredError` | `NullRunBlockedException` | `NR-MCP03` | An MCP tool needs operator approval. |
| `NullRunConsumeOverbudgetError` | `NullRunDecision` | `NR-O001` | The actual cost exceeded the reservation. |
| `NullRunChainError` | `NullRunDecision` | `NR-CH001` | The chain scope check failed. |
| `WorkflowPausedException` | `NullRunDecision` | `NR-W003` | The workflow is paused. Carries `.resume_after`. |
| `NullRunWorkflowInactiveError` | `NullRunDecision` | `NR-W004` | The workflow is inactive. |
| `WorkflowKilledInterrupt` | `NullRunError` | `NR-W002` | The operator killed the workflow. Not a `NullRunDecision`. |
| `NullRunWorkflowKilledError` | `WorkflowKilledInterrupt` | `NR-W002` | Typed name for the kill signal. |
| `NullRunConfigError` | `NullRunInfrastructureError` | `NR-C000` | Misconfiguration. |
| `NullRunAuthenticationError` | `NullRunInfrastructureError` | `NR-A001` | The credentials were rejected. |
| `NullRunAuthError` | `NullRunAuthenticationError` | `NR-A003` | The API key was rejected. |
| `NullRunProtocolError` | `NullRunInfrastructureError` | `NR-P001` | The wire-protocol version does not match. |
| `NullRunMalformedGateResponseError` | `NullRunProtocolError` | `NR-P002` | The gate response is not a decision the SDK can act on. |
| `NullRunGateIndeterminateError` | `NullRunInfrastructureError` | `NR-P004` | The SDK could not obtain a decision. |
| `NullRunUnclassifiedRefusalError` | `NullRunInfrastructureError` | `NR-P003` | The refusal category is not one the SDK understands. |
| `NullRunUnknownActionError` | `NullRunInfrastructureError` | `NR-P005` | The control plane sent an action type this SDK cannot run. |
| `NullRunRateLimitRedisError` | `NullRunInfrastructureError` | `NR-R002` | The rate limiter is unavailable. |
| `NullRunTransportError` | `NullRunInfrastructureError` | `NR-B001` | The request never reached the gateway. Carries `.source` and `.endpoint`. |
| `NullRunBackendError` | `NullRunTransportError` | `NR-B002` | The gateway returned 5xx. |
| `NullRunExecutionNotFoundError` | `NullRunBackendError` | `NR-EX01` | The execution id is unknown or its binding expired. |
| `RateLimitError` | `NullRunTransportError` | `NR-R001` | The gateway returned 429. Carries `.retry_after` and `.upgrade_url`. |
| `BreakerError` | `Exception` | — | Root alias for the SDK error hierarchy. |
| `BreakerTransportError` | `BreakerError` | — | Events could not be delivered. Not a `NullRunError`. |
| `InsecureTransportError` | `BreakerTransportError` | — | HTTPS was required. |

`TransportErrorSource` has four values: `NETWORK_ERROR`, `GATEWAY_ERROR`,
`AUTH_ERROR`, `BREAKER_OPEN`.

## Catch-all pattern

```python title="catch_all_pattern.py"
import time

import nullrun
from nullrun import WorkflowKilledInterrupt, protect
from nullrun.breaker.exceptions import (
    NullRunBlockedException,
    RateLimitError,
    WorkflowPausedException,
)

try:
    step()
except WorkflowKilledInterrupt:
    raise                    # always re-raise — the kill must reach the top
except NullRunBlockedException:
    ...                      # budget, tool block, approval, chain
except RateLimitError as exc:
    time.sleep(exc.retry_after)
except WorkflowPausedException:
    ...                      # resume the workflow, then retry
```

`init()` is optional here. The first `protect`-decorated call creates the
runtime lazily from `NULLRUN_API_KEY`.

For global observability, register `nullrun.on_error(...)` instead of wrapping
every call site.

## User-facing messages

`nullrun.format_user_message(exc)` renders a `NullRunError` — or any object with
an `error_code` attribute — as end-user-facing text.

```python title="format_user_message.py"
import nullrun
from nullrun import NullRunBudgetError

@nullrun.protect
def chatbot(message: str) -> str:
    return agent.run(message)

try:
    reply = chatbot(message)
except NullRunBudgetError as exc:
    return nullrun.format_user_message(exc)
```

The catalog of default messages belongs to NullRun, so every deployment shows
the same wording for a given `error_code`. A deployment can override one code
with `set_user_message`. Overrides live in a per-process dict. They are not
persisted and not sent to the gateway.

An object without `error_code` gets a generic fallback. The function never
raises and never returns an empty string.

## See also

- [Decorators & context managers](decorators.md) — `@protect` and the
  extractor wrappers
- [Errors](errors.md)
- [Errors → Decision vs. infrastructure](errors.md#decision-vs-infrastructure)
- [Use with FastAPI](../how-to/fastapi.md)
- [Manual cost / event tracking](../how-to/custom-tracking.md)
- [Auto-instrumentation](../getting-started/install.md#what-gets-instrumented)
- [Control plane](../concepts/control-plane.md)
