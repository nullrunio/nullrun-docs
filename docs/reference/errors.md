# Error codes

> Placeholder — auto-generated from the gateway's error enum.

## SDK exceptions

| Class | When | Recoverable? |
| --- | --- | --- |
| `NullRunBlockedException` | Generic policy block | Maybe — see the attached reason |
| `BudgetExceededException` | Per-workflow budget exhausted | No for this run |
| `LoopDetectedException` | Loop pattern detected | No for this run |
| `SensitiveToolBlocked` | Sensitive tool without STRICT mode | No |
| `NullRunAuthenticationError` | Missing or invalid API key | Fix credentials, retry |
| `WorkflowKilledException` | Killed via control plane | No for this run |
| `WorkflowPausedException` | Paused via control plane | Resume via control plane, then retry |
| `NullRunTimeout` | Gateway timeout | Yes — automatic retry |

## HTTP status codes (gateway)

| Status | Meaning | SDK action |
| --- | --- | --- |
| 200 | OK | — |
| 401 | Bad API key | Raise `NullRunAuthenticationError` |
| 402 | Budget exhausted (pre-flight) | Raise `BudgetExceededException` |
| 403 | Policy violation | Raise `NullRunBlockedException` |
| 404 | Workflow / policy not found | Retry without policy (PERMISSIVE) |
| 409 | Loop / sensitive tool blocked | Raise `LoopDetectedException` / `SensitiveToolBlocked` |
| 429 | Rate limited | Backoff and retry |
| 5xx | Gateway error | Backoff, then fail-closed (sensitive) or use cache (workflow) |

## See also

- [SDK API](sdk-api.md)
