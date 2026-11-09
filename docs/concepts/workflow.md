---
title: Workflows
maturity: stable
description: Group agent calls into a named workflow, bind policies and keys to it, and scope a chain across several calls.
---

# Workflows

A **workflow** is one agent you run. It appears under **Workflows** in
the sidebar. Each workflow has its own budget, its own policies and
its own API keys.

## What you see in the dashboard

The **Workflows** page lists every workflow in your organization. Each
row shows:

- The workflow's name
- Whether it is **Active**, **Paused** or **Killed**
- Spend for the current period against the cap
- How many API keys are bound to it
- When it last saw traffic

Open a workflow for its detail page. The page has six tabs:

| Tab | What it shows |
|---|---|
| **Overview** | Name, state, spend against the cap, applied policies, and the **Pause**, **Resume**, **Kill** and **Delete** controls. You change the budget cap here. |
| **Policies** | The policies scoped to this workflow, filtered to this workflow |
| **Executions** | Every gate call this workflow made — allowed, blocked, rate-limited |
| **Traces** | The nested view of one run: every LLM call, every tool call, with timing and cost |
| **API keys** | The keys bound to this workflow. **Generate API key** mints a new one; the value is shown once. |
| **Coverage** | The tools and MCP servers observed on this workflow, and what is not governed yet |

## How to create one

1. Click **Workflows** in the sidebar.
2. Click **New workflow**.
3. Give it a name. Names allow letters, digits, spaces and `_ . , - & ( )`,
   up to 255 characters.
4. Optionally set an **External ID** — your own identifier for the
   workflow, so your systems can look it up.
5. Click **Create**.

You land on the new workflow's detail page. From there:

- **Mint an API key** under the **API keys** tab. The value
  (`nr_live_...`) is shown **once**.
- **Point your SDK at it** by exporting `NULLRUN_API_KEY`. The
  workflow binding happens server-side.

<figure class="nr-shot">
  <img class="nr-shot__light" src="../../assets/images/screenshots/workflows-list-light.png"
       alt="Workflows list with the New workflow button highlighted in the top right."
       loading="lazy" decoding="async">
  <img class="nr-shot__dark" src="../../assets/images/screenshots/workflows-list-dark.png"
       alt="Workflows list with the New workflow button highlighted in the top right."
       loading="lazy" decoding="async">
  <figcaption class="nr-shot__caption">Workflows · New workflow</figcaption>
</figure>

<figure class="nr-shot">
  <img class="nr-shot__light" src="../../assets/images/screenshots/workflow-new-light.png"
       alt="Create workflow dialog open — Workflow name field and External ID optional field."
       loading="lazy" decoding="async">
  <img class="nr-shot__dark" src="../../assets/images/screenshots/workflow-new-dark.png"
       alt="Create workflow dialog open — Workflow name field and External ID optional field."
       loading="lazy" decoding="async">
  <figcaption class="nr-shot__caption">Workflows · Create dialog</figcaption>
</figure>

## How to control one

A workflow has three states you control from the dashboard or the API:
**Active**, **Paused** and **Killed**.

| State | What the agent sees |
|---|---|
| Active | Calls run normally |
| Paused | Protected calls are refused with `WorkflowPausedException` (`NR-W003`) |
| Killed | Protected calls are refused with the kill signal (`NR-W002`) |

Pause and Kill reach a running agent over a WebSocket push, so the
agent does not have to wait for its next call to learn. See
[Control plane](control-plane.md) for the full contract.

Killed is terminal. There is no way back to Active from Killed.

## The workflow's settings

- **Budget** — the per-period cap in cents. The dashboard shows a bar
  of spend against the cap.
- **Enforcement mode** — `Hard` (block on budget exceeded) or `Soft`
  (allow a bounded overdraft when a chain is active). See
  [Policies → BudgetLimit extra fields](policies.md#budgetlimit-extra-fields).
- **Human approvals** — require operator approval for sensitive
  tools. Needs the Approvals feature, on Growth and above.
- **Tool block list** — the patterns the agent must not call. See
  [Tool policies](tool-policies.md).
- **Trace retention** — how long to keep detailed traces.

## Chain context

A **chain** groups several protected calls that belong to one user
request. You declare it with the `chain` context manager:

```python
import uuid
import nullrun

chain_id = str(uuid.uuid4())

with nullrun.chain(chain_id, op="start"):
    research()   # first call opens the chain
    draft()      # later calls continue it
```

`chain_id` **must be a UUID v4**. The SDK validates it in your
process and raises `ValueError` on a malformed value, so a typo or a
predictable identifier fails locally instead of silently registering a
new chain on the server. Generate one with `uuid.uuid4()`.

`op` is the chain operation for the first call inside the block:

| `op` | What it does |
|---|---|
| `start` | Open the chain |
| `continue` | Continue an existing chain |
| `end` | Close the chain in the same call as the gate decision |
| `auto` | Register the chain if it is not known, otherwise continue it |

The default is `start`.

### When a chain ends

A chain closes on the **first** of:

- `op="end"`
- five minutes without a protected call
- `max_chain_duration_seconds` exceeded, which defaults to 3600

For a long stream, send a heartbeat roughly every 30 seconds. See
[Heartbeat](../how-to/streaming.md#chain-heartbeat).

### Why chains exist

Chains exist so the gate can tell "one call that happens to be
expensive" from "a sequence of calls that together cost more than
the budget". With an active chain, a Soft-mode policy lets the agent
run past its budget up to the overdraft cap. See
[Policies → BudgetLimit extra fields](policies.md#budgetlimit-extra-fields).

## How the workflow ends

A workflow has no end state. It stays **Active** across many runs, and
each run is a sequence of protected calls. The workflow keeps its
policies, budget and key bindings. Run the agent again next week and
the same workflow handles it.

## See also

- [Budgets](budgets.md) — the budget cap and how the period rolls over
- [Policies](policies.md) — the rules attached to a workflow
- [Control plane](control-plane.md) — how Pause and Kill reach the agent
- [API keys](api-keys.md) — how to mint a key bound to this workflow
