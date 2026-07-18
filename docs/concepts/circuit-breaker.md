# Circuit breaker

A **circuit breaker** is what stops your agent when something goes
wrong. When the agent is hitting the budget cap, stuck in a loop, or
trying to call a sensitive tool — the breaker trips and the agent
stops, even if the agent's code doesn't know to stop.

In the dashboard, a tripped breaker shows up as the workflow's
status flipping from **Active** to **Killed** or as a flood of
**block** decisions in the Decision History.

## When does it trip?

The breaker reacts to four situations. Each is a separate decision
the gate makes, but to you it all looks the same: the next call
rejects.

| Situation | What you see | Where in the dashboard |
|---|---|---|
| **Budget exceeded** | Every call returns `block` with reason `BUDGET_EXCEEDED` | Decision History, then the spend bar hits 100% |
| **Loop detected** | The same tool called 6+ times in 60 seconds | Decision History shows repeated `block` decisions |
| **Rate limit hit** | 429-style block with `Retry-After` | Decision History, rate-limit counter on the workflow page |
| **Sensitive tool blocked** | `block` with reason `SENSITIVE_TOOL` | Decision History with source `sdk` |
| **Operator kill** | `WorkflowKilledInterrupt` raised mid-call | Workflow status flips to **Killed** |

The first three are automatic — the gate enforces them on every
call. The fourth needs you to click **Kill** in the dashboard or
call `POST /workflows/{id}/kill`.

## What the agent sees

When the breaker trips, the SDK raises an exception. The exact
exception depends on what tripped it:

| Trip cause | Exception | BaseException? |
|---|---|---|
| Budget exceeded | `NullRunBudgetError` | No |
| Loop detected | `NullRunBlockedException` | No |
| Rate limit | `RateLimitError` | No |
| Sensitive tool blocked | `NullRunBlockedException` | No |
| Operator kill | `WorkflowKilledInterrupt` | **Yes** |

The kill signal is a `BaseException`, not an `Exception`. This is
deliberate: it propagates through `try/except Exception:` blocks so
you can't accidentally swallow the kill. See
[Error handling → Kill signal](../concepts/error-handling.md)
for the full contract.

If you use the zero-boilerplate helpers from the SDK, you don't have
to write any of this — `@guarded` catches the standard exceptions
and prints the catalog wording, `WorkflowKilledInterrupt` still
propagates.

## When the gateway is unreachable

Sometimes the gateway itself is down — DNS, network, an outage.
The breaker has to decide what to do without a policy decision. There
are three modes:

| Mode | What happens when the gateway is unreachable | Use when |
|---|---|---|
| **Strict** | Block everything (fail closed) | Sensitive operations — this is the default for [sensitive tools](sensitive-tools.md) |
| **Permissive** | Allow everything (fail open) | Best-effort UX where the cost of blocking is higher than the cost of a missed policy check |
| **Cached** | Use the last known good decision | Steady-state workloads where stale is safer than none — **deprecated**, kept only for backward compatibility |

The default for the `/gate` pre-flight is **Permissive**. The
exception is sensitive tools, which always fail closed.

You don't pick the mode per-call — it's a deployment-wide setting.
If your deployment handles sensitive operations, the SDK will block
those locally (sensitive tool = always strict) while letting normal
operations through (Permissive).

## When the breaker recovers

After the gateway comes back, the breaker transitions automatically
to normal mode. No operator action needed — the next `/gate` call
succeeds if the policy allows it.

If the breaker is tripping too often (every call rejects), look at:

1. **Decision History** for the workflow. The reason column tells
   you why each call was blocked.
2. **Spend** tab. If you're consistently hitting the budget, raise
   the cap or switch to a cheaper model.
3. **Effective policy**. A policy you added recently may be too
   strict — try narrowing patterns or scoping to one workflow
   before rolling out org-wide.

## Common scenarios

### "My agent suddenly stopped responding"

Open the workflow in the dashboard. Check the state:

| Status | What happened |
|---|---|
| **Active** | The agent is fine — check the application logs for the actual error |
| **Paused** | You paused it (or an operator did). Click **Resume** to restart. |
| **Killed** | You killed it (or an operator did). Create a new workflow or re-activate. |

If the status is Active but every call rejects, open **Decision
History** and filter by `decision = block`. The reason column shows
the pattern that matched.

### "My agent was working yesterday and is blocked today"

Look at **Spend**. The budget probably rolled over (new month) and
the new period started with empty budget. Raise the cap or wait
for the next reset.

### "I want to test my agent without the breaker tripping"

Use a **test key** (`test_key: true` in the key creation form). Test
keys bypass the budget cap so you can develop freely. Don't use a
test key in production — the cap is what protects you.

## See also

- [Budgets](budgets.md) — the most common trip cause
- [Sensitive tools](sensitive-tools.md) — strict-mode default for
  dangerous operations
- [Human approval](human-approval.md) — the alternative to blocking
  for sensitive operations you actually want to allow
- [Troubleshooting](../troubleshooting.md) — common "why is my
  agent blocked?" questions
