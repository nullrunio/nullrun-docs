# SDK API

The Python SDK lives in
[`nullrunio/nullrun-sdk-python`](https://github.com/nullrunio/nullrun-sdk-python).
Package name on PyPI: **`nullrun`**.

```bash title="shell"
pip install nullrun            # core only
pip install "nullrun[langgraph]"
pip install "nullrun[agents]"  # openai-agents
pip install "nullrun[all]"     # every optional extra
```

Auto-instrumentation for httpx-based libraries (`openai`,
`anthropic`, `openai-agents`, …) is on by default once `init()` runs —
see [Auto-instrumentation](../getting-started/install.md#auto-instrumentation).

## Top-level

```python title="public_surface.py"
from nullrun import init, init_or_die, protect, workflow, span, agent, chain, track_llm, track_tool, track_event
```

### `init()` vs `init_or_die()` — which one to use

| Helper | Behaviour | Use when |
|---|---|---|
| `init(api_key=None, api_url=None, debug=False)` | Raises `NullRunAuthenticationError` (NR-C001) if `api_key` is missing or env var unset. Returns the runtime. | Production / apps where you want to handle "no api_key" yourself (e.g. surface a friendly error to your UI) |
| `init_or_die(api_key=None, api_url=None, debug=False)` | Catches the NR-C001 exception, prints the catalog user-message to stderr, calls `sys.exit(1)`. Returns the runtime otherwise. | One-shot scripts, CLI tools, examples, anything where a missing key is a hard error |

`init_or_die` is `init` plus an `try/except NullRunAuthenticationError → sys.exit(1)`. The chain `@guarded` decorator does the same for callsite-level errors.

|| Symbol | Purpose | In `__all__` |
|---|---|---|---|
| `init(api_key=None, api_url=None, debug=False)` | Initialise the SDK singleton. `api_key` is required (read from `NULLRUN_API_KEY` if not passed). The HMAC secret, batch size, flush interval, and transport mode are **not** parameters here — set them via env vars or by constructing `NullRunRuntime` directly. Probes `GET /api/v1/capabilities` on first call to validate v3 contract. | ✅ |
| `init_or_die(api_key=None, api_url=None, debug=False)` | Like `init` but exits cleanly with code 1 if no API key is configured. See the table above. | ✅ |
| `@protect` | Wrap a function for **gate** enforcement (budget pre-flight + kill/pause check + sensitive-tool decision). Takes no kwargs. Always pair with `@guarded` for the zero-boilerplate exit-on-block pattern. | ✅ |
| `@sensitive` | Parameterless decorator. Marks a function as a sensitive tool — `@protect` will pre-check `runtime.execute(...)` before the body runs. **Fails CLOSED on transport error** (ADR-008) regardless of the runtime's fallback mode. Place `@sensitive` outside `@protect` so registration runs first. | ✅ (lazy import) |
| `@guarded` | Decorator that wraps a function so any `NullRunError` raised inside is converted to `format_user_message(exc)` on stderr and `sys.exit(1)`. `WorkflowKilledInterrupt` (BaseException) propagates unchanged. | ✅ |
| `with nullrun.handle(*, exit_code=1):` | Context manager form of `@guarded` — apply to a region of code rather than a single function. | ✅ |
| `workflow(name=None)` | Context manager. Sets the `workflow_id` contextvar that `@protect` and `track_*` attach to events. | (lazy) |
| `chain(name=None, *, op="auto")` | Context manager for soft-mode budget gate. `op="start"` registers the chain; `op="continue"` extends TTL; `op="end"` closes it. | (lazy) |
| `span(name=None)` | Context manager for nested trace spans. | (lazy) |
| `agent(name=None)` | Context manager for agent identity. | (lazy) |
| `set_call_context(model=None, tools=None)` | Per-call context the SDK forwards to `/gate` so the backend's budget + tool-block enforcement sees real values (was `"budget-precheck"` sentinel + empty tool list pre-0.6.0). | (lazy) |
| `on_error(hook)` | Register a global error hook (Layer 2 of "give the user a chance"). Fires for every `NullRunError` subclass BEFORE the exception propagates. Multiple hooks supported; fires in registration order; hook exceptions are caught and DEBUG-logged. Does NOT fire for `WorkflowKilledInterrupt` (BaseException — kill is a non-recoverable signal). Returns an idempotent unregister callable. | ✅ |
| `track_llm(input_tokens, output_tokens=0, *, model=None, latency_ms=None, metadata=None)` | Manual escape hatch for non-HTTP LLM calls. Returns the backend's decision dict. Buffers into the event batch and flushes on the next `@protect` call or `flush_interval_ms`. | ✅ |
| `track_tool(tool_name, duration_ms=None, *, is_retry=False, metadata=None)` | Manual tool-call tracking. | ✅ |
| `track_event(event_type, **kwargs)` | Catch-all for custom events. | ✅ |
| `format_user_message(exc, locale="en")` | Render a `NullRunError` as an end-user-facing string from the SDK's default catalog. Use this in place of `str(exc)` when showing exceptions to end users — see [User-facing messages](#user-facing-messages) below. | ✅ |
| `set_user_message(code, text)` | Override the user-facing message for a specific `error_code` for the lifetime of this process. Pass `text=""` to clear. | ✅ |
| `get_user_message(code)` | Look up the raw user-facing message for an `error_code`. Returns the per-process override if set, otherwise the catalog default, otherwise the generic fallback. | (lazy) |
| `shutdown(timeout=2.0, flush=True)` | Gracefully shut down the runtime: send a clean WebSocket close frame, drain in-flight events, stop background threads (HTTP poller, WS push listener, transport flush). Safe to register via `atexit`. | ✅ |
| `status()` | Synchronous snapshot of the runtime state as a frozen `NullRunStatus` dataclass (`ok` / `degraded` / `offline` / `misconfigured`). Thread-safe, side-effect-free. Raises `NullRunConfigError` if the runtime hasn't been initialised yet. | ✅ |

### `track_llm` manual usage

Use `track_llm` when auto-instrumentation can't see the LLM call — a
custom HTTP client that bypasses `httpx`, an offline batch job, a
test fixture. The signature mirrors the data the auto-instrumentation
extractor reads from OpenAI / Anthropic / Gemini / Cohere response
bodies:

```python title="track_llm_manual.py"
import nullrun
from nullrun import track_llm

# After your custom LLM call returns:
track_llm(
    input_tokens=response.usage.prompt_tokens,
    output_tokens=response.usage.completion_tokens,
    model="custom-model-v1",
    latency_ms=response.elapsed_ms,
    metadata={"vendor": "custom", "trace_id": "..."},
)
```

Without `track_llm`, the SDK has nothing to report to the gateway —
the budget counter is never credited, and the next `/gate` call may
reject based on stale spend. Call `track_llm` once per real LLM
call.

### `track_tool` manual usage

```python title="track_tool_manual.py"
from nullrun import track_tool

track_tool(
    tool_name="send_email",
    duration_ms=240,
    is_retry=False,
    metadata={"to": "user@example.com"},
)
```

Use it when a non-LLM tool call happens outside the auto-instrumentation
hooks (e.g. a custom agent framework, or a tool wrapped in your own
function). The `tool_name` flows through to the policy engine — a
`ToolBlock` policy with `pattern = "send_*"` will catch a manual call
to `track_tool("send_email", ...)`.

### `track_event` catch-all

```python title="track_event_manual.py"
from nullrun import track_event

track_event("agent.milestone", step="research_complete", elapsed_secs=42)
```

Accepts arbitrary keyword arguments as the event payload. Use for
custom observability signals (milestones, errors, business events)
that you want in the decision log alongside `track_llm` /
`track_tool`.

### Custom user messages

```python title="set_user_message.py"
import nullrun

# Override the default message for budget-exceeded. Pass "" to clear.
nullrun.set_user_message(
    "NR-B004",
    "You've used all your support credits. Upgrade to keep chatting.",
)

# Look up the message for an error_code at runtime:
msg = nullrun.get_user_message("NR-R001")
```

Overrides live in a per-process dict and are checked before the
catalog default. They do not persist across processes and are not
synced to the backend — they are pure presentation sugar. See
[User-facing messages](#user-facing-messages) below for the full
rationale.

The curated public surface in `dir(nullrun)` is the six core symbols
above plus `on_error`, plus the structured exception names
`NullRunError`, `NullRunAuthError`, `NullRunConfigError`,
`NullRunBackendError`, `NullRunBudgetError`, `NullRunToolBlockedError`,
and `WorkflowKilledInterrupt` (the kill signal). The legacy names
(`WorkflowPausedException`, `WorkflowKilledException`,
`NullRunAuthenticationError`, `NullRunBlockedException`) remain
importable via `from nullrun import X` for backward compatibility
but no longer appear in `dir(nullrun)`.

## Exceptions

All raised from `nullrun.breaker.exceptions`. Every public SDK
exception inherits from `NullRunError` and carries four structured
fields: `error_code` (e.g. `"NR-B004"`), `user_action` (imperative
hint), `retryable` (bool), `docs_url`. See
[Errors](errors.md#sdk-exception-hierarchy-python) for the full
hierarchy diagram.

| Class | When | Notes |
| --- | --- | --- |
| `NullRunError` | Structured base for every user-facing SDK exception | Inherits `BreakerError`. Carries `.error_code`, `.user_action`, `.retryable`, `.docs_url`. |
| `NullRunConfigError` | SDK misconfigured (e.g. missing `api_key`) | `error_code="NR-C000"`-family. Never retryable. |
| `NullRunAuthenticationError` | Missing / invalid `X-API-Key`, bad HMAC | 401 / 403. Carries `.message` for backward compat. |
| `NullRunAuthError` | 401 specifically (key rejected) | Subclass of `NullRunAuthenticationError` (`NR-A003`). Carries `.status_code` (the wire HTTP status). |
| `NullRunTransportError` | Gateway unreachable | Carries `.source` (`NETWORK_ERROR` / `GATEWAY_ERROR` / `BREAKER_OPEN` / `AUTH_ERROR`) and `.endpoint`. Retryable. |
| `NullRunBackendError` | 5xx from the gateway | Subclass of `NullRunTransportError`. `NR-B002`. Retryable. |
| `RateLimitError` | HTTP 429 | Subclass of `NullRunTransportError`. Carries `.retry_after`, `.upgrade_url`, `.body`. `NR-R001`. Retryable. |
| `NullRunRateLimitRedisError` | 503 — Redis reservation failed | Subclass of `NullRunInfrastructureError`. `NR-R002`. **Fail-CLOSED.** |
| `NullRunProtocolError` | Backend returned 400 `PROTOCOL_TOO_OLD` | Carries `.min_required_version`. Upgrade SDK past `SDK_MIN_VERSION_FOR_V3`. |
| `NullRunBlockedException` | Generic policy block | Inspect `.workflow_id`, `.reason`, `.action`, `.tool_name`, `.details`. Carries `.status_code` (the wire HTTP status, e.g. 402 budget, 403 cross-org, 422 `CONSUME_OVERBUDGET`, 429 cap-reached). **No** `.message` — use `str(exc)`. `NR-X001`. |
| `NullRunBudgetError` | Budget exhausted | Subclass of `NullRunBlockedException`. `NR-B004`. |
| `NullRunToolBlockedError` | Tool in block list | Subclass of `NullRunBlockedException`. `NR-T001`. Carries `.tool_name`. |
| `NullRunChainError` | Chain-mode gate check failed | Subclass of `NullRunDecision`. `NR-CH001`. |
| `NullRunConsumeOverbudgetError` | 422 — actual cost > reservation + ε | Subclass of `NullRunDecision`. Surfaces over-budget commit events. |
| `NullRunWorkflowInactiveError` | 403 — workflow paused / killed cross-org | Subclass of `NullRunDecision`. `NR-W004`. |
| `BreakerTransportError` | Transport misconfiguration (events cannot be delivered after retries) | Subclass of `BreakerError` (NOT `NullRunError`). Carries `.events_lost`, `.buffer_size`. |
| `InsecureTransportError` | HTTP used where HTTPS required | Subclass of `BreakerTransportError`. |
| `WorkflowPausedException` | Paused via control plane | Subclass of `NullRunError`. `NR-W003`. Carries `.workflow_id`, `.reason`, `.resume_after`. |
| `WorkflowKilledException` | Killed via control plane (parent) | `Exception` subclass. **Deprecated** — emits `DeprecationWarning` on construction. Use `WorkflowKilledInterrupt` directly. |
| `WorkflowKilledInterrupt` | Kill arrived mid-call | Subclass of `BaseException` (NOT `Exception`) per the kill contract — catch before `except Exception`. |

Removed in 0.4.0: `CostLimitExceeded`, `ApprovalRequired`,
`BreakerTimeout`, `LoopDetectedException`, `RetryStormException`,
`RateLimitExceededException`. These classes had no remaining callers
and are no longer reachable under any import path.

## Catch-all pattern

```python title="catch_all_pattern.py"
import nullrun
from nullrun import WorkflowKilledInterrupt, init, protect, workflow

# NullRunBlockedException lives in `nullrun.breaker.exceptions` — the
# top-level `nullrun.breaker` package does not re-export it. Several
# older re-exports (CostLimitExceeded, ApprovalRequired, BreakerTimeout,
# LoopDetectedException, RetryStormException, RateLimitExceededException)
# were removed in SDK 0.4.0 and are no longer reachable under any path.
from nullrun.breaker.exceptions import (
    NullRunBlockedException,
    RateLimitError,
    WorkflowPausedException,
)

init(api_key="nr_live_...")

with workflow("my-agent"):
    @protect
    def step():
        ...

    try:
        step()
    except WorkflowKilledInterrupt:
        raise                    # kill contract — BaseException, not Exception
    except WorkflowPausedException:
        raise                    # paused — resume via WS / API, then retry
    except NullRunBlockedException as exc:
        ...                      # budget / loop / retry / sensitive
    except RateLimitError as exc:
        time.sleep(exc.retry_after)
```

For global observability (Sentry, OpenTelemetry, structured logs),
register a hook with `nullrun.on_error(...)` instead of wrapping every
call site. The hook fires for every `NullRunError` subclass BEFORE the
exception propagates, with the `ErrorContext` describing where the
failure fired (`stage`, `workflow_id`, `tool_name`, `api_key_prefix`).
Hook exceptions are caught and DEBUG-logged — a misbehaving hook
cannot break the SDK.

## User-facing messages

`nullrun.format_user_message(exc, locale="en")` renders a `NullRunError`
(or any object with an `error_code` attribute) as an end-user-facing
string. **Use this instead of `str(exc)` whenever the message might be
shown to a person who is not the developer** — `str(exc)` contains
internal identifiers like `workflow_id` and `budget_cents` that leak
the SDK's internals into product UI.

```python title="format_user_message.py"
import nullrun
from nullrun import NullRunBudgetError

@nullrun.protect
def chatbot(message: str) -> str:
    return agent.run(message)

try:
    reply = chatbot(message)
except NullRunBudgetError as exc:
    # Show the user a clean message instead of the raw exception text
    # ("Workflow wf-31a blocked: budget_cents=500 exceeded...").
    return nullrun.format_user_message(exc)
```

### Why the SDK owns the wording

The catalog of default messages is part of the NullRun product, not the
customer's integration code. Every Customer Support Bot built on
NullRun that hits `NR-B004` shows the same "You've reached the usage
limit for this conversation. Please try again later." string. This
keeps the UX consistent across deployments and lets the product team
A/B test wording for upgrade-conversion without touching customer
code. **Customers should not write their own `code -> text` mapping.**

### Per-deployment branding

If a deployment wants its own wording for a single code (e.g. a
branded "out of credits ☕" message), call `set_user_message` once at
startup:

```python title="set_user_message.py"
import nullrun

# Override the default message for budget-exceeded. Pass "" to clear.
nullrun.set_user_message(
    "NR-B004",
    "You've used all your support credits. Upgrade to keep chatting.",
)
```

Overrides live in a per-process dict and are checked before the
catalog default. They do not persist across processes and are not
synced to the backend — they are pure presentation sugar.

### Locale

`format_user_message(exc, locale)` accepts a locale code; in this SDK
version **only English (`"en"`) is shipped** and any other value falls
back to the English message. The parameter is reserved for future
locale packs and matches the structure that user-message overrides
will take when they land.

### What if `error_code` is unknown or missing?

Objects without `error_code` (plain `Exception`, raw values) get a
generic fallback (`"Something went wrong. Please try again."`). The
function never raises and never returns an empty string.

## See also

- [Errors](errors.md)
- [Errors → Decision vs. infrastructure](errors.md#decision-vs-infrastructure)
- [Use with FastAPI](../how-to/fastapi.md)
- [Auto-instrumentation](../getting-started/install.md#auto-instrumentation)
- [Control plane](../concepts/control-plane.md)
