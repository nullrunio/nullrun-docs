title: Circuit breaker
maturity: stable
description: How NullRun's circuit breaker trips on a budget overrun, recovers after a cooldown, and propagates a kill signal across in-flight calls.
# Circuit breaker

The circuit breaker stops your agent when something goes wrong. When
the agent is hitting the budget cap, calling a tool your policies
forbid, or being asked by an operator to stop — the gate returns
`block` and the SDK raises an exception, even if the agent's code
doesn't know to stop.

The underlying mechanism is a single `/api/v1/gate` evaluation per
`@protect`-wrapped call that returns `allow` / `block` /
`require_approval`.

In the dashboard, a tripped breaker shows up as the workflow's status
flipping from **Active** to **Killed** or as a flood of **block**
decisions in the **Audit log**.

## When does it trip?

The gate reacts to three categories of situation. Each is a separate
decision path inside `/gate`, but to you it all looks the same: the
next call rejects.

| Situation | What you see | Where in the dashboard |
|---|---|---|
| **Budget exceeded** (Hard mode) | Every call returns `block`; SDK raises `NullRunBudgetError` with `error_code = "NR-B004"` | Audit log, then the spend bar hits 100% |
| **Tool blocked** by policy | `block`; SDK raises `NullRunToolBlockedError` with `error_code = "NR-T001"` | Audit log |
| **Operator kill** | `WorkflowKilledInterrupt` (alias `NullRunWorkflowKilledError`) raised mid-call | Workflow status flips to **Killed** |

Rate limiting (429) and budget soft-mode blocks are returned by the
same gate but with different codes. SDK surfaces them as `error_code = "NR-R001"` and `error_code = "NR-B004"`. See [Budgets](budgets.md#soft-mode) and [Policies](policies.md).

The first two are automatic — the gate enforces them on every call.
The third needs you to click **Kill** in the dashboard or call
`POST /api/v1/workflows/{id}/kill`.

## What the agent sees

When the breaker trips, the SDK raises an exception. The exact
exception depends on what tripped it:

| Trip cause | Exception | Class |
|---|---|---|
| Budget exceeded | `NullRunBudgetError` (`error_code = "NR-B004"`) | `NullRunError` (Exception) |
| Tool blocked | `NullRunBlockedException` (`error_code = "NR-T001"`) | `NullRunError` (Exception) |
| Operator kill | `WorkflowKilledInterrupt` (alias `NullRunWorkflowKilledError`) | `NullRunError` (Exception) |

The kill signal inherits from `NullRunError`, so `try/except Exception:`
catches it like every other SDK error. To handle kill specifically
— checkpoint state, notify a supervisor, exit cleanly — catch
`NullRunWorkflowKilledError` (preferred) or `WorkflowKilledInterrupt`
explicitly. See [Error handling → Kill signal](../concepts/error-handling.md#kill-signal)
for the recommended handler shape.

If you use the zero-boilerplate helpers from the SDK, you don't have
to write any of this — `with nullrun.guard():` catches the standard
`NullRunError` exceptions, prints the structured four-line developer
report, and exits 1. The kill signal is the one exception:
`guard()` re-raises it so kill always reaches the top of the agent
loop. To handle kill distinctly, use bare `@protect` with an
explicit `except NullRunWorkflowKilledError:` arm.

## When the gateway is unreachable

Sometimes the gateway itself is down — DNS, network, an outage.
The mental model: critical paths (budget reservation, ToolBlock,
aggregate rate limit) refuse to run when the gateway can't be reached;
secondary signals (per-key rate limit) may let calls through. When the
gateway rejects because of an infrastructure failure, you'll see a
clear HTTP error from the SDK.

If you're seeing persistent infrastructure failures, contact support.

## When the breaker recovers

After the gateway comes back, the gate transitions automatically to
normal mode. No operator action needed — the next `/gate` call
succeeds if the policy allows it.

If the gate is blocking too often (every call rejects), look at:

1. The **Audit log** for the workflow. The reason column tells you
   why each call was blocked.
2. The workflow's **Overview** tab — the spend vs. cap bar shows
   whether you're consistently hitting the budget. Raise the cap or
   switch to a cheaper model if so.
3. **Effective policy** (on the **Policies** tab). A policy you added
   recently may be too strict — try narrowing patterns or scoping to
   one workflow before rolling out org-wide.

## Common scenarios

### "My agent suddenly stopped responding"

Open the workflow in the dashboard. Check the state:

| Status | What happened |
|---|---|
| **Active** | The agent is fine — check the application logs for the actual error |
| **Paused** | You paused it (or an operator did). Click **Resume** to restart. See [Control plane](control-plane.md). |
| **Killed** | You killed it (or an operator did). Create a new workflow or re-activate. |

If the status is Active but every call rejects, open the
**Audit log** and filter by `decision = block`. The reason column
shows the pattern that matched.

### "My agent was working yesterday and is blocked today"

Look at the workflow's **Overview** tab — the spend bar. The budget
probably rolled over (new month or billing cycle renewal) and the new
period started with an empty counter. Raise the cap or wait for the
next reset.

### "I want to test my agent without the breaker tripping"

Use a **separate workflow** with its own (low or zero) budget. Don't
disable the gate — bypassing it is a dev/test opt-out.

## See also

- [Budgets](budgets.md) — the most common trip cause
- [Tool policies](tool-policies.md) — your own blocking rules
- [Human approval](human-approval.md) — the alternative to blocking
  for sensitive operations you actually want to allow
- [Troubleshooting](../troubleshooting.md) — common "why is my
  agent blocked?" questions

!!! info "Deep dive"

    A single gate evaluation can trip on three independent paths,
    and the budget and tool-block paths are fail-closed. Budget
    enforcement runs as one atomic reservation: the org-level
    ceiling applies first, then the workflow ceiling, then the
    current period's counter. Nothing is committed unless all three
    pass, so a caller can never observe a partially applied
    reservation. On overflow the reservation flips to a blocked
    state and the gate reports the spent, budget, and projected
    totals, so the rejection can be reconstructed from the error
    alone.

    Tool blocking resolves one canonical tool list from the request
    and matches it against the patterns on the effective policy.
    Names containing control characters are rejected. Pattern
    matching is glob-based: `*` alone matches everything,
    `prefix.*` matches both `prefix` and `prefix.anything`, and a
    pattern with several stars splits on each star and requires the
    literal segments to appear in order — so `*.drop_*` matches
    `s3.drop_table`. A request that supplies no tool list while
    patterns are configured is blocked, not allowed.

    Checks run in a fixed order — workflow active, parent
    ownership, cycle depth, tool block, business-impact validation,
    rate limit, then budget reservation — and evaluation
    short-circuits on the first decision that is not `allow`.
    Precedence runs `block` above `require_approval` above `allow`,
    so a blocked call is reported before any budget envelope is
    minted.

    Retrying a gate call is safe: an idempotent retry returns the
    stored response rather than minting a fresh reservation. The
    execution identifier is minted server-side and bound to the
    organization and API key, and that binding is the only source of
    truth for the reserve-then-consume pair. An organization-level
    budget is a single shared counter, so exhausting it through one
    workflow also blocks every other workflow under the same
    organization.

    The aggregate per-organization rate limit fails closed; the
    per-key limit fails open, with the budget gate as the backstop.
    A storage partition surfaces as a fast rejection rather than a
    hung request, and reservations in flight at the moment of a trip
    are cleaned up when their envelope expires, which bounds the
    cleanup window but does not remove it. Kill delivery falls back
    to heartbeat polling when the push channel is unavailable, so
    the worst-case latency of a kill is bounded by the heartbeat
    interval rather than being immediate.
