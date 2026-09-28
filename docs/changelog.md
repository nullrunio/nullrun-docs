---
title: Changelog
description: Every released version of the NullRun Python SDK, with the changes a reader of these docs can observe — new API surface, behaviour changes, and fixes.
maturity: stable
---

# Changelog

Every released version of the `nullrun` Python SDK, newest first. Entries
cover what someone building on NullRun can observe: the API surface, the
behaviour a protected run exhibits, and the wire contract.

The docs are the source of truth for **how** each of these behaves —
this page records **when** it changed. A version listed here is
described in full in the chapters it affects; if a symbol appears in an
entry, it is documented on one of those pages.

!!! info "Reading version numbers"

    The SDK is versioned `0.MINOR.PATCH`. The **minor** position is
    where the public surface moves — a symbol appears, changes shape, or
    goes away. The **patch** position carries behaviour fixes and
    additions that do not alter the surface.

    All versions below the current one are available on PyPI:

    ```bash
    pip install nullrun==0.18.5
    ```

## 0.18.5 — 2026-09-26

The public surface is reduced to the smallest set that still does the
job. Four entry points collapse into two, and a set of internals stops
being importable.

### Changed

- **`nullrun.guard` replaces `nullrun.handle`.** Same `@contextmanager`
  body: it catches `NullRunError`, re-raises `WorkflowKilledInterrupt`
  untouched, prints a developer-facing report, and exits non-zero on
  failure. See [Error handling](concepts/error-handling.md) for the
  full context-manager set and where `guard` sits among them.

- **`nullrun.init(fail_on_exit=True)` replaces `init_or_die()`.**
  Fail-fast is now a keyword argument on `init` rather than a separate
  function. The default is `False`, which preserves the raise-on-bad-config
  behaviour that embedders want.

- **`nullrun.shutdown()` is registered automatically.** `init()` arranges
  for a clean WebSocket close at process exit, so a long-running script
  no longer needs an explicit shutdown call. Calling it yourself is
  still valid and still idempotent.

- **Install is a single line.** Per-framework install groups are gone;
  `pip install nullrun` is the whole instruction. The framework
  auto-detection in [Framework integrations](how-to/llm-frameworks.md)
  is unchanged.

### Removed

These names are no longer importable from the top-level `nullrun`
namespace. `dir(nullrun)` now returns exactly:

```text
__version__, init, protect, shutdown, on_error, guard,
NullRunError, NullRunAuthError, NullRunConfigError,
NullRunBackendError, NullRunBudgetError, NullRunToolBlockedError,
WorkflowKilledInterrupt, NullRunWorkflowKilledError,
NullRunMcpDestructiveBlockedError,
NullRunMcpReadonlyBypassBlockedError,
NullRunMcpApprovalRequiredError,
NullRunApprovalDbUnavailableError,
format_user_message, set_user_message
```

- `nullrun.status()` — the snapshot is reached through
  `nullrun.get_runtime().status()`, which returns the same
  `NullRunStatus` dataclass. `NullRunStatus` itself remains importable
  as a type.
- `@nullrun.guarded` — the decorator form is `with nullrun.guard():`.
- `nullrun.auto_instrument`, `nullrun.is_auto_instrumented`, and the
  module-level `track_event` alias. The `runtime.track_event` method is
  unaffected.
- `NullRunCallback` from the lazy-export table. The framework
  integrations do not need it.

The wire contract is unchanged from 0.18.0.

## 0.18.2 — 2026-09-22

`@protect` is established as the single entry point. Every call routes
through the execute endpoint unconditionally — there is no opt-out and
no per-tool registry to maintain.

```python
import nullrun

nullrun.init()

@nullrun.protect
def my_tool(query: str) -> str:
    ...
```

See [Decorators & extractors](reference/decorators.md) for the full
decorator reference and [Tool policies](concepts/tool-policies.md)
for what the gate evaluates.

## 0.18.1 — 2026-09-22

Aimed squarely at the moment a developer first runs an example and it
does not work.

- **A four-line error report on the fail-fast paths.** A configuration
  or gate failure at startup prints what failed, where it failed (wire
  endpoint, status code, transport source), why it failed (the
  underlying exception and its machine `error_code`), and what to do
  about it. The end-user-facing message is still the headline, so an
  end-user deployment still sees a single clean sentence. See
  [Troubleshooting](troubleshooting.md).

- **A warning when a protected tool fires 50 times with no model
  activity.** The usual cause is a tool wired up without the agent loop
  that feeds it, which otherwise bills nothing and looks like it works.

## 0.18.0 — 2026-09-21

- **Approved actions are consumed on success.** When an action runs
  after approval, the grant is closed automatically. Grants left open
  past their expiry no longer accumulate, so the approvals surface
  reflects only what is actually waiting on a human.

## 0.17.1 — 2026-09-15

- **Every gate call carries its own operation id.** A single id is no
  longer reused across calls in the same scope, which removes a class of
  spurious budget errors where an unrelated call inherited the identity
  of the first one. The error codes in
  [Error codes](reference/errors.md) are unchanged.

## 0.17.0 — 2026-09-12

- **The circuit breaker serialises sync and async callers against each
  other.** A threaded call and an `asyncio` call on the same breaker
  instance previously took different locks, so their state transitions
  could interleave. Both paths now contend on one lock. See
  [Circuit breaker](concepts/circuit-breaker.md).

- **The impact helpers resolve off the top-level `nullrun` namespace**
  rather than needing a deep import into a private module. The helpers
  that [Sensitive tools](concepts/sensitive-tools.md) describes are
  what this fixes; the exception they were raising on first call is
  gone.

## 0.16.x — August–September 2026

The hardening series. The surface settled here; everything above is a
change to it.

- **Kill propagates as an exception rather than an exit.** A
  `WorkflowKilledInterrupt` raised by [Kill](concepts/control-plane.md)
  is not swallowed by an enclosing error handler, so an agent that is
  stopped from the dashboard stops. See
  [Control plane](concepts/control-plane.md).

- **Fail-closed policy fetches.** A policy the gate cannot retrieve is a
  refusal, not a pass. `ToolBlock` and aggregate rate limiting fail
  closed; per-key limits and budget checks fail open, because the budget
  layer behind them is the backstop. See
  [Policies](concepts/policies.md).

- **Cost accounting is decimal, not floating point.** Amounts are
  serialized without binary-float drift, so a reserved cost and its
  consumption net to zero. See [Budgets](concepts/budgets.md).

- **Reservations are released on the exception path.** A protected call
  that raises leaves no reservation behind.

---

Reports something that does not match what you are reading here? The
SDK repository takes issues, and the [GitHub](https://github.com/nullrunio/nullrun-docs)
link in the footer points at this docs repository.
