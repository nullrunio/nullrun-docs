# Circuit breaker

A circuit breaker sits between your agent and the work it does. When
something goes wrong (cost blowup, runaway loop, hostile input), the
breaker **trips** and the agent stops, even if the code itself doesn't
know to stop.

## States

- **CLOSED** — normal. Calls flow through.
- **OPEN** — tripped. Calls are blocked with `NullRunBlockedException`.
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

When the gateway is unreachable, the breaker uses one of three
modes. The mode is **fixed per call-site** in the SDK code; there
is no public `NULLRUN_FALLBACK_MODE` env var (a pre-0.6.0 docs
draft mentioned one — it was never wired up).

| Mode | Behaviour | Use when |
| --- | --- | --- |
| `STRICT` | Block all calls (fail closed) | Sensitive operations, regulated workloads — `_enforce_sensitive_tool` always uses STRICT |
| `PERMISSIVE` *(default for `/gate` pre-flight)* | Allow all calls (fail open) | Best-effort UX; cost may slightly overshoot during an outage |
| `CACHED` | Use the most recent successful decision | Steady-state workloads where a stale policy is safer than none. **Deprecated** — accepted on `FlushConfig.fallback_mode` for backward compatibility but no longer the default for any call-site |

> The default is `PERMISSIVE` for the `/gate` pre-flight. The
> exception is **sensitive tools**, which always fail closed
> (regardless of mode) — see [Sensitive tools](sensitive-tools.md).
> To opt into STRICT for a single sensitive function for tests,
> set `NULLRUN_SENSITIVE_FAIL_OPEN=1`; production must never set
> this.

The internal `decision_source` enum (visible to operators via the
`decision` log line and the `on_error` hook's `ErrorContext`) tags
every fallback verdict with one of `FALLBACK_NETWORK_ERROR`,
`FALLBACK_GATEWAY_ERROR`, or `FALLBACK_BREAKER_OPEN` so a SRE can
distinguish "Redis was down" from "Python lost the socket" from
"the breaker tripped on its own budget" — see ADR-008 in the
gateway repo for the full fail-CLOSED/OPEN matrix.

## When the gateway recovers

After an outage, the breaker transitions `OPEN → HALF_OPEN`. The
first call is treated as a probe:

- success → close the breaker, resume normal flow.
- failure → reopen, wait `breaker.recovery_timeout`

The SDK surfaces the fallback decision via `NullRunTransportError`
with `source=BREAKER_OPEN` so operators can alert on it (see
[Errors](../reference/errors.md)).

## See also

- [Budgets](budgets.md)
- [Sensitive tools](sensitive-tools.md)
- [Control plane](control-plane.md)
- [How-to → Set a hard cost cap](../how-to/cost-cap.md)
