# SDK API

The Python SDK lives in
[`nullrunio/nullrun-sdk-python`](https://github.com/nullrunio/nullrun-sdk-python).
Package name on PyPI: **`nullrun`**.

```bash
pip install nullrun            # core only
pip install "nullrun[langgraph]"
pip install "nullrun[agents]"  # openai-agents
pip install "nullrun[all]"     # every optional extra
```

Auto-instrumentation for httpx-based libraries (`openai`,
`anthropic`, `openai-agents`, …) is on by default once `init()` runs —
see [Auto-instrumentation](../getting-started/install.md#auto-instrumentation).

## Top-level

```python
from nullrun import init, protect, workflow, span, agent, track_llm, track_tool, track_event
```

| Symbol | Purpose |
| --- | --- |
| `init(api_key=None, api_url=None, debug=False)` | Initialise the SDK singleton. `api_key` is required (read from `NULLRUN_API_KEY` if not passed). The HMAC secret, batch size, flush interval, and transport mode are **not** parameters here — set them via env vars or by constructing `NullRunRuntime` directly. |
| `@protect` | Wrap a function for **gate** enforcement (budget pre-flight + kill/pause check + sensitive-tool decision). Takes no kwargs. |
| `@sensitive` | Parameterless decorator. Marks a function as a sensitive tool — `@protect` will pre-check `runtime.execute(...)` before the body runs. Fails CLOSED on transport error (ADR-008) regardless of the runtime's fallback mode. Chain with `@protect` in either order; the recommended form is `@sensitive` outside so `add_sensitive_tool(fn.__name__)` runs before the wrapper is built. |
| `workflow(name=None)` | Context manager. Sets the `workflow_id` contextvar that `@protect` and `track_*` attach to events. |
| `span(name=None)` | Context manager for nested trace spans. |
| `agent(name=None)` | Context manager for agent identity. |
| `track_llm(input_tokens, output_tokens=0, *, model=None, latency_ms=None, metadata=None)` | Manual escape hatch for non-HTTP LLM calls. |
| `track_tool(tool_name, duration_ms=None, *, is_retry=False, metadata=None)` | Manual tool-call tracking. |
| `track_event(event_type, **kwargs)` | Catch-all for custom events. |

All `track_*` functions return a `dict[str, Any]` describing the
backend's response (`{"allowed": bool, "actions": [...], ...}`); they
buffer into the event batch and flush on the next `@protect` call or
`flush_interval_ms`.

## Exceptions

All raised from `nullrun.breaker.exceptions`:

| Class | When | Notes |
| --- | --- | --- |
| `BreakerError` | Base for all SDK errors | Subclass of `Exception` |
| `NullRunAuthenticationError` | Missing / invalid `X-API-Key`, bad HMAC | 401 / 403 |
| `NullRunTransportError` | Gateway unreachable | Carries `.source` (`NETWORK_ERROR` / `GATEWAY_ERROR` / `BREAKER_OPEN` / `AUTH_ERROR`) and `.endpoint` |
| `RateLimitError` | HTTP 429 | Subclass of `NullRunTransportError`; carries `.retry_after`, `.upgrade_url` |
| `BreakerTransportError` | Transport misconfiguration | Subclass of `BreakerError` |
| `InsecureTransportError` | HTTP used where HTTPS required | Subclass of `BreakerTransportError` |
| `NullRunBlockedException` | Generic policy block | Inspect `.message`, `.details`, `.tool_name` |
| `WorkflowPausedException` | Paused via control plane | Resume via WS / API, then retry |
| `WorkflowKilledException` | Killed via control plane | Base class (emits `DeprecationWarning` on construction) |
| `WorkflowKilledInterrupt` | Kill arrived mid-call | **Subclass of `BaseException`** — catch before `except Exception` |

Removed in 0.4.0: `CostLimitExceeded`, `ApprovalRequired`,
`BreakerTimeout`, `LoopDetectedException`, `RetryStormException`,
`RateLimitExceededException`. These classes had no remaining callers
and are no longer reachable under any import path.

## Catch-all pattern

```python
import nullrun
from nullrun import WorkflowKilledInterrupt, init, protect, workflow

# NullRunBlockedException lives in `nullrun.breaker.exceptions` — the
# top-level `nullrun.breaker` package does not re-export it. Several
# older re-exports (CostLimitExceeded, ApprovalRequired, BreakerTimeout,
# LoopDetectedException, RetryStormException, RateLimitExceededException)
# were removed in SDK 0.4.0 and are no longer reachable under any path.
from nullrun.breaker.exceptions import NullRunBlockedException

init(api_key="nr_live_...")

with workflow("my-agent"):
    @protect
    def step():
        ...

    try:
        step()
    except WorkflowKilledInterrupt:
        raise                    # kill contract — re-raise if you can't resume
    except NullRunBlockedException as exc:
        ...                      # budget / loop / retry / sensitive
    except nullrun.breaker.exceptions.RateLimitError as exc:
        time.sleep(exc.retry_after)
```

## See also

- [Errors](errors.md)
- [Auto-instrumentation](../getting-started/install.md#auto-instrumentation)
- [Control plane](../concepts/control-plane.md)
