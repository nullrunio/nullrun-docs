title: Workflows
maturity: stable
description: Group agent calls into a named workflow, propagate parent_trace_id, and bind cost to a logical unit instead of a single session.
# Workflows

A **workflow** is one agent you run. In the dashboard it shows up
under **Workflows** in the left sidebar. Each workflow has its own
budget, its own list of API keys, its own decision history.

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

<figure class="nr-shot">
  <img class="nr-shot__light" src="../../assets/images/screenshots/workflows-list-light.png"
       alt="Workflows list with the New workflow button highlighted in the top right.">
  <img class="nr-shot__dark" src="../../assets/images/screenshots/workflows-list-dark.png"
       alt="Workflows list with the New workflow button highlighted in the top right.">
  <figcaption class="nr-shot__caption">Workflows · New workflow</figcaption>
</figure>

<figure class="nr-shot">
  <img class="nr-shot__light" src="../../assets/images/screenshots/workflow-new-light.png"
       alt="Create workflow dialog open — Workflow name field and External ID optional field.">
  <img class="nr-shot__dark" src="../../assets/images/screenshots/workflow-new-dark.png"
       alt="Create workflow dialog open — Workflow name field and External ID optional field.">
  <figcaption class="nr-shot__caption">Workflows · Create dialog</figcaption>
</figure>

<figure class="nr-shot">
  <img class="nr-shot__light" src="../../assets/images/screenshots/workflow-detail-light.png"
       alt="Workflow detail page — Overview tab with budget card, applied policies, Pause and Kill controls.">
  <img class="nr-shot__dark" src="../../assets/images/screenshots/workflow-detail-dark.png"
       alt="Workflow detail page — Overview tab with budget card, applied policies, Pause and Kill controls.">
  <figcaption class="nr-shot__caption">Workflows · Workflow detail</figcaption>
</figure>

You'll land on the new workflow's detail page. From there:

- **Mint an API key** under the **Keys** tab. The key value
  (`nr_live_...`) is shown **once** — copy it into your secret
  manager immediately.
- **Point your SDK at it**: `nullrun.init(api_key=...)` picks up
  the key; the workflow binding happens server-side.

## How to control one

Each workflow has three states that you control from the dashboard
or via the API: **Active**, **Paused**, and **Killed**. Both Pause
and Kill reach your running SDK over a WebSocket push; the agent
doesn't have to wait for the next call to learn. See
[Control plane](control-plane.md) for the full contract, the
exceptions each state raises, and how the signal travels over the
WebSocket.

## The workflow's settings

Five things you control per workflow:

- **Budget** — the per-period cap in cents. Set this first. The
  dashboard shows a horizontal bar of how much you've spent vs. the
  cap.
- **Enforcement mode** — `Hard` (block on budget exceeded) or
  `Soft` (allow over-budget up to an overdraft cap, when there's an
  active chain). Full configuration in
  [Policies → BudgetLimit extra fields](policies.md#budgetlimit-extra-fields).
- **Human approvals** — turn on to require operator approval for
  dangerous tools (payments, deletes, external API mutations).
  Available on Growth+ plans.
- **Tool block list** — the patterns the agent must not call. See
  [Tool policies](tool-policies.md).
- **Trace retention** — how long to keep detailed per-call traces
  (default 30 days, plan-gated up to 90).

## Chain context

A **chain** is a logical grouping across multiple `@protect` calls
inside one user request, declared via `with chain(...)`. Chains are
auto-registered on the first `/gate` call: the chain transitions
from `null → ACTIVE` atomically.

### When chains end

A chain dies on the **first** of:

- `op="end"` is reached in the context manager
- 5 minutes of `/gate` inactivity (idle TTL)
- `max_chain_duration_seconds` exceeded (default 3600)

For long streams, send a `POST /heartbeat` every 30 seconds — see
[Heartbeat → how-to](../how-to/streaming.md#chain-heartbeat).

### Why chains exist

Chains exist primarily to enable **soft-mode budget gating**: with
an active chain, the gate allows the agent to run past its budget
up to an overdraft cap (`max_overdraft_cents` or
`max_overdraft_percent`, whichever is lower). Full soft-mode
contract in
[Policies → BudgetLimit extra fields](policies.md#budgetlimit-extra-fields).

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
