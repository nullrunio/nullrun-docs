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
| **Operator kill** | `WorkflowKilledInterrupt` raised mid-call | Workflow status flips to **Killed** |

Rate limiting (429) and budget soft-mode blocks are returned by the
same gate but with different codes. SDK surfaces them as `error_code = "NR-R001"` and `error_code = "NR-B004"`. See [Budgets](budgets.md#soft-mode) and [Policies](policies.md).

The first two are automatic — the gate enforces them on every call.
The third needs you to click **Kill** in the dashboard or call
`POST /api/v1/workflows/{id}/kill`.

## What the agent sees

When the breaker trips, the SDK raises an exception. The exact
exception depends on what tripped it:

| Trip cause | Exception | `BaseException`? |
|---|---|---|
| Budget exceeded | `NullRunBudgetError` (`error_code = "NR-B004"`) | No |
| Tool blocked | `NullRunBlockedException` (`error_code = "NR-T001"`) | No |
| Operator kill | `WorkflowKilledInterrupt` | **Yes** |

The kill signal is a `BaseException`, not an `Exception`, so it
propagates through `try/except Exception:` blocks. See
[Error handling → Kill signal](../concepts/error-handling.md#kill-signal-special-case)
for the full contract.

If you use the zero-boilerplate helpers from the SDK, you don't have
to write any of this — `@guarded` catches the standard exceptions
and prints the catalog wording, `WorkflowKilledInterrupt` still
propagates.

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
disable the gate — bypassing it is a dev/test opt-out that the SDK
flags with a `RuntimeWarning`.

## See also

- [Budgets](budgets.md) — the most common trip cause
- [Tool policies](tool-policies.md) — your own blocking rules
- [Human approval](human-approval.md) — the alternative to blocking
  for sensitive operations you actually want to allow
- [Troubleshooting](../troubleshooting.md) — common "why is my
  agent blocked?" questions
