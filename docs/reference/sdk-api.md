# SDK API

> Placeholder — full reference will be auto-generated from
> `nullrunio/nullrun-sdk-python` docstrings.

## Top-level

- `init(api_key=..., **kwargs)` — initialise the SDK
- `@protect(workflow_id=None, **kwargs)` — wrap a function for
  enforcement and tracking
- `protect.workflow(...)` — explicit workflow context manager (planned)

## Exceptions

- `NullRunBlockedException` — base for all policy / breaker blocks
- `BudgetExceededException` — per-workflow budget exceeded
- `LoopDetectedException` — loop pattern detected
- `NullRunAuthenticationError` — missing or invalid API key
- `WorkflowKilledException` — killed via the control plane
- `WorkflowPausedException` — paused via the control plane
- `NullRunTimeout` — gateway timeout (call retried automatically)

## See also

- [Errors](errors.md)
