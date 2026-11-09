---
title: 5-minute tour
description: A walk through the NullRun dashboard that ends with an agent tripping a budget cap.
maturity: stable
---

# 5-minute tour

This is the shortest path from "I have never used NullRun" to "my agent stopped itself at the budget cap". Six screens, one script, one cap.

> **Install first?** Jump to [Install](install.md) and come back. This tour assumes the `nullrun` package is installed and `NULLRUN_API_KEY` is exported.

## What you will build

A small agent that:

1. Calls `gpt-4o-mini` through the NullRun gate
2. Runs on a workflow with a budget of `$10`
3. Books about two cents of spend in one run
4. Stops at the cap once you lower it to one cent

Every call lands in the dashboard.

## Step 1 — Set up the workspace

Open [nullrun.io/onboarding](https://nullrun.io/onboarding). The wizard walks through five steps: **Workspace**, **Workflow**, **API key**, **Connect**, **Ready**.

1. **Workspace** — name it.
2. **Workflow** — name it `tour-agent`. The wizard creates the workflow, a **Budget Limit** policy of `$10` scoped to it, and an API key bound to it.

## Step 2 — Create an API key

To use the key the wizard made, you can skip this step. To create another one:

1. In the sidebar, under **Access**, click **API keys**.
2. Click **New API key** in the top right.
3. In the dialog, pick the **Workflow** the key belongs to and name the key `tour-agent`. Pick an expiration: **Never**, **24 hours**, **7 days**, **30 days**, or **90 days**.
4. Click **Create** and copy the `nr_live_…` identifier.

<figure class="nr-shot">
  <img class="nr-shot__light" src="../../assets/images/screenshots/api-keys-list-light.png"
       alt="API keys page showing the New key button highlighted in the top right."
       loading="lazy" decoding="async">
  <img class="nr-shot__dark" src="../../assets/images/screenshots/api-keys-list-dark.png"
       alt="API keys page showing the New key button highlighted in the top right."
       loading="lazy" decoding="async">
  <figcaption class="nr-shot__caption">API keys · New key</figcaption>
</figure>

The dashboard shows the key once. The signing secret is never shown, and the SDK does not need it — it fetches the secret from the gateway on first use.

```bash title="shell"
export NULLRUN_API_KEY="nr_live_xxxxxxxxxxxxxxxx"
```

## Step 3 — Wire up the agent

Create a file `tour_agent.py`:

```python title="tour_agent.py"
import nullrun
from nullrun import protect, NullRunBudgetError
from openai import OpenAI

client = OpenAI()

# One long prompt, so every call books real tokens.
CONTEXT = "NullRun checks every tool call before it runs. " * 500


@protect
def ask(question: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": CONTEXT + question}],
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    for i in range(30):
        try:
            print(f"[{i}]", ask("Tell me a one-sentence joke."))
        except NullRunBudgetError as exc:
            print(f"[{i}] BLOCKED:", nullrun.format_user_message(exc))
            break
```

The long prompt is deliberate. A one-sentence question costs so little that no cap would ever trip. With `CONTEXT` in the prompt each call carries about 5,000 input tokens, so thirty calls cost about two cents on `gpt-4o-mini`.

Run it:

```bash title="shell"
pip install nullrun openai
python tour_agent.py
```

All thirty calls succeed.

## Step 4 — Watch the decisions

Open **Governance → Audit log**. You see:

- One row per protected call, in four columns: **Time**, **Decision**, **Rule**, **Actor**.
- The period presets **24h**, **7d**, **30d**, **90d**, and **All**, plus a **Custom** range. The page opens on **30d**.
- **Allow** on every row so far.

The audit log is a plan feature. A workspace in its trial has it.

<figure class="nr-shot">
  <img class="nr-shot__light" src="../../assets/images/screenshots/audit-log-light.png"
       alt="Audit log page — Allow / Deny / Require approval filter chips and the events table."
       loading="lazy" decoding="async">
  <img class="nr-shot__dark" src="../../assets/images/screenshots/audit-log-dark.png"
       alt="Audit log page — Allow / Deny / Require approval filter chips and the events table."
       loading="lazy" decoding="async">
  <figcaption class="nr-shot__caption">Governance · Audit log</figcaption>
</figure>

## Step 5 — Trip the cap

In the sidebar, open **Governance → Policies**. You find the `tour-agent - starting budget` policy, a **Budget Limit** on the `tour-agent` workflow.

1. Edit it and set **Max cost (USD/month)** to `0.01`. That is one cent, and it is the smallest cap the server accepts.
2. Leave **Enforcement mode** on **Hard**.

Run the script again:

```bash title="shell"
python tour_agent.py
```

The agent stops itself before the first call:

```
[0] BLOCKED: You've reached the usage limit for this conversation. Please try again later.
```

The cap covers the whole period, not one run. The first run booked about two cents, so a one-cent cap leaves nothing to spend and the gate refuses the next call. If your first run booked less than a cent, the block lands a few calls later instead.

That line comes from the SDK's message catalog. Replace it with your own wording if you want to:

```python
import nullrun

nullrun.set_user_message("NR-B004", "Your monthly limit is reached. Upgrade to keep going.")
```

The audit log has a new row. **Decision** is **Deny**, and **Rule** names the budget policy. Open the row to read the reason code and the policy hash.

The SDK error code for this refusal is `NR-B004`. It rides on the exception, and `nullrun.guard()` prints it in the developer report.

## Step 6 — Raise the cap

Edit the same policy and set **Max cost (USD/month)** to `5` (`$5.00`). Run the script once more. All thirty calls succeed.

The **Overview** tab of the workflow shows the spend against the cap.

## What next?

| You want to… | Open |
| --- | --- |
| Block a tool the agent must not touch | [Concepts → Tool policies](../concepts/tool-policies.md) |
| Ask a human to approve a sensitive action | [Concepts → Human approval](../concepts/human-approval.md) |
| Understand the gate in depth | [Concepts → Circuit breaker](../concepts/circuit-breaker.md) |
| Run several agents | [How-to → Run multiple agents](../how-to/multi-agent.md) |
| Stream responses | [How-to → Stream responses](../how-to/streaming.md) |
| Tune the SDK | [Configuration → Behaviour](configuration.md#behaviour) |

!!! tip "Where to send feedback"
    Email `support@nullrun.io`. Include the workflow ID and the `decision_id` of the row that surprised you.
