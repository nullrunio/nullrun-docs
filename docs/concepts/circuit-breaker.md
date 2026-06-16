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

## Fallback modes

When the gateway is unreachable, the breaker uses one of three modes:

| Mode | Behaviour |
| --- | --- |
| `STRICT` | Block all calls (fail closed) |
| `PERMISSIVE` | Allow all calls (fail open) |
| `CACHED` | Use the most recent successful decision |

The default is `CACHED` for the workflow-level breaker and `STRICT`
(fail-closed) for **sensitive tools** — the safest combination.

## See also

- [Budgets](budgets.md)
- [Sensitive tools](sensitive-tools.md)
- [How-to → Set a hard cost cap](../how-to/cost-cap.md)
