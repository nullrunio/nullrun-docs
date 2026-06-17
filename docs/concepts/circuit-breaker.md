# Circuit breaker

A circuit breaker sits between your agent and the work it does. When
something goes wrong (cost blowup, runaway loop, hostile input), the
breaker **trips** and the agent stops, even if the code itself doesn't
know to stop.

## States

- **CLOSED** — normal. Calls flow through.
- **OPEN** — tripped. Calls are blocked with `NullRunBlockedException`
  (or a subclass: `LoopDetectedException`, `RetryStormException`,
  `RateLimitExceededException`).
- **HALF_OPEN** — testing recovery. One trial call goes through; if it
  succeeds, the breaker closes again.

## Triggers

What causes the breaker to open depends on the **policy** attached to
the workflow. Common triggers:

- Cost per call > threshold
- Cumulative workflow cost > budget
- Loop detected (same tool call N times)
- Retry storm (consecutive failures > threshold)
- Tool call to a sensitive resource without approval
- Kill signal received via the [control plane](control-plane.md)

## Fallback modes

When the gateway is unreachable, the breaker uses one of three modes
(set via `NULLRUN_FALLBACK_MODE`):

| Mode | Behaviour | Use when |
| --- | --- | --- |
| `STRICT` | Block all calls (fail closed) | Sensitive operations, regulated workloads |
| `PERMISSIVE` *(default)* | Allow all calls (fail open) | Best-effort UX; cost may slightly overshoot during an outage |
| `CACHED` | Use the most recent successful decision | Steady-state workloads where a stale policy is safer than none |

> The default is `PERMISSIVE`. The exception is **sensitive tools**,
> which always fail closed (regardless of `NULLRUN_FALLBACK_MODE`) —
> see [Sensitive tools](sensitive-tools.md).

## When the gateway recovers

After an outage, the breaker transitions `OPEN → HALF_OPEN`. The
first call is treated as a probe:

- success → close the breaker, resume normal flow.
- failure → reopen, wait `breaker.cooldown_ms` before retrying.

The SDK surfaces the fallback decision via `NullRunTransportError`
with `source=BREAKER_OPEN` so operators can alert on it (see
[Errors](../reference/errors.md)).

## See also

- [Budgets](budgets.md)
- [Sensitive tools](sensitive-tools.md)
- [Control plane](control-plane.md)
- [How-to → Set a hard cost cap](../how-to/cost-cap.md)
