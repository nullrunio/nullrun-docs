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
| `init(api_key=None, *, api_url=None, secret_key=None, debug=False, log_level="INFO", fallback_mode="PERMISSIVE", batch_size=100, flush_interval_ms=5000)` | Initialise the SDK singleton. `api_key` is required; the rest have sensible defaults. |
| `@protect` | Wrap a function for **gate** enforcement (budget pre-flight + kill/pause check + sensitive-tool decision). Takes no kwargs. |
| `@sensitive(tool, reason=None)` | Per-tool fail-CLOSED gate (ADR-008). Blocks the call when the gateway is unreachable, regardless of `NULLRUN_FALLBACK_MODE`. |
| `workflow(name=None)` | Context manager. Sets the `workflow_id` contextvar that `@protect` and `track_*` attach to events. |
| `span(name=None)` | Context manager for nested trace spans. |
| `agent(name=None)` | Context manager for agent identity. |
| `track_llm(*, model, input_tokens, output_tokens, latency_ms=None, cost_cents=None, **extra)` | Manual escape hatch for non-HTTP LLM calls. |
| `track_tool(*, name, args=None, result=None, latency_ms=None, **extra)` | Manual tool-call tracking. |
| `track_event(*, type, **payload)` | Catch-all for custom events. |

All `track_*` functions return `None`; they buffer into the event batch
and flush on the next `@protect` call or `flush_interval_ms`.

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
| `CostLimitExceeded` | Local breaker tripped (not a gateway call) | Loop / cost / retry storm caught by local detector |
| `ApprovalRequired` | Sensitive tool requires explicit approval flow | Caller must trigger the approval UI |
| `BreakerTimeout` | Gateway timeout | Auto-retried with backoff |
| `NullRunBlockedException` | Generic policy block | Inspect `.message` and `.details` |
| `LoopDetectedException` | Loop pattern detected | Subclass of `NullRunBlockedException` |
| `RetryStormException` | Consecutive failures > threshold | Subclass of `NullRunBlockedException` |
| `RateLimitExceededException` | Local rate signal | Subclass of `NullRunBlockedException`; distinct from gateway `RateLimitError` |
| `WorkflowPausedException` | Paused via control plane | Resume via WS / API, then retry |
| `WorkflowKilledException` | Killed via control plane | Base class |
| `WorkflowKilledInterrupt` | Kill arrived mid-call | **Subclass of `BaseException`** — catch before `except Exception` |

## Catch-all pattern

```python
import nullrun
from nullrun import WorkflowKilledInterrupt, init, protect, workflow
from nullrun.breaker import NullRunBlockedException

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
    except nullrun.breaker.RateLimitError as exc:
        time.sleep(exc.retry_after)
```

## See also

- [Errors](errors.md)
- [Auto-instrumentation](../getting-started/install.md#auto-instrumentation)
- [Control plane](../concepts/control-plane.md)
