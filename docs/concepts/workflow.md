# Workflows

A **workflow** is one agent you run. In the dashboard it shows up
under **Workflows** in the left sidebar. Each workflow has its own
budget, its own list of API keys, its own decision history.

If you have one production assistant and one weekend experiment,
that's two workflows.

## What you see in the dashboard

The **Workflows** page lists every workflow you've created. Each
row shows:

- The workflow's name (you picked this when you created it)
- Whether it's **Active**, **Paused**, or **Killed**
- Total spend for the current billing period
- How many API keys are bound to it
- When it last saw traffic

Click a workflow to open its detail page. The detail page has five
tabs:

| Tab | What it shows |
|---|---|
| **Decisions** | Every gate call your agent made — allowed, blocked, rate-limited. The raw list the gate uses to decide what your agent can do. |
| **Spend** | Cost broken down by day, by model, by tool. Time-to-exhaustion estimate at the current rate. |
| **Keys** | The API keys bound to this workflow. The raw key value is shown only once at creation. |
| **Traces** | Hierarchical view of one agent run — each LLM call, each tool call, with timing and cost. |
| **Settings** | Budget cap, kill/pause, soft-mode toggle, plan-feature gates. |

## How to create one

1. In the dashboard sidebar, click **Workflows**.
2. Click **New workflow** in the top right.
3. Give it a name (e.g. `"production-support-bot"`). The name shows
   up everywhere — keep it short.
4. Set a starting budget. You can change it any time. The default is
   zero, which blocks every call until you raise it.
5. Click **Create**.

You'll land on the new workflow's detail page. From there:

- **Mint an API key** under the **Keys** tab. The key value
  (`nr_live_...`) is shown **once** — copy it into your secret
  manager immediately.
- **Point your SDK at it**: `nullrun.init(api_key=...)` picks up
  the key; the workflow binding happens server-side.

## How to control one

Each workflow has three states that you control from the dashboard
or via the API:

| State | What it means | What your agent sees |
|---|---|---|
| **Active** | Calls are gated normally | `allow` / `block` as usual |
| **Paused** | You want a temporary stop | Every call raises `WorkflowPausedException` until you unpause |
| **Killed** | You want it stopped | Every call raises `WorkflowKilledInterrupt` — `BaseException`, your loop must catch it explicitly |

Both Pause and Kill reach your running SDK over a WebSocket push —
typically within a second. The agent doesn't have to wait for the
next call to learn.

To pause a runaway agent immediately, click the workflow's
**Pause** button (or hit `POST /workflows/{id}/pause`). The SDK
raises the pause exception at the next gate entry.

To stop it permanently, hit **Kill**. The kill signal is a
`BaseException`, so it propagates even if you've wrapped the agent
in `try/except Exception`. The agent loop dies.

Both actions are reversible — Pause can be unpaused, Kill is
terminal until you restart the workflow.

## The workflow's settings

Five things you control per workflow:

- **Budget** — the per-period cap in cents. Set this first. The
  dashboard shows a horizontal bar of how much you've spent vs. the
  cap.
- **Enforcement mode** — `Hard` (block on budget exceeded) or
  `Soft` (allow over-budget up to an overdraft cap, when there's an
  active chain). See the [Soft mode](#soft-mode) section below.
- **Human approvals** — turn on to require operator approval for
  dangerous tools (payments, deletes, external API mutations).
  Available on Growth+ plans.
- **Tool block list** — the patterns the agent must not call. See
  [Tool policies](tool-policies.md).
- **Trace retention** — how long to keep detailed per-call traces
  (default 30 days, plan-gated up to 90).

## Soft mode

A workflow with `enforcement_mode = Soft` lets the agent run past
its budget when it has an **active chain** — a logical grouping
across multiple `@protect` calls inside one user request. The agent
keeps running until it hits an **overdraft cap** (`max_overdraft_cents`
or `max_overdraft_percent`).

Soft mode is for long multi-step tasks where one budget decision
across the whole task makes more sense than one per step. To use it,
your SDK code must declare a chain:

```python
from nullrun import chain

with chain("user-123-research-task"):
    # many @protect calls in here share one budget decision
    research_step()
    draft_step()
    publish_step()
```

If a chain runs past its budget and then past the overdraft cap, the
gate blocks the next call and the workflow returns to normal Hard
mode for that chain.

## How the workflow ends

A workflow doesn't have an explicit "end" state in the sense of a
final commit. Instead:

- The workflow stays **Active** across many agent runs. Each run is
  a sequence of `@protect` calls.
- A run is **logically ended** when the agent's loop returns or
  throws.
- A workflow is **paused** or **killed** when you decide, or when
  plan limits (max workflows per plan) cause auto-pause.

There is no "clean up the workflow when done" step. Active workflows
keep their policy, budget, and key bindings. Re-run the agent next
week and the same workflow handles it.

## See also

- [Budgets](budgets.md) — the budget cap and how rollover works
- [Policies](policies.md) — what rules attach to a workflow
- [Control plane](control-plane.md) — how Kill / Pause reach your agent
- [API keys](api-keys.md) — how to mint a key bound to this workflow
