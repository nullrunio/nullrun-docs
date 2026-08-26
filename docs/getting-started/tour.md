title: 5-minute tour
maturity: stable
description: Five-minute walkthrough of the NullRun dashboard, policies, and SDK — enough to evaluate the platform end-to-end.
# 5-minute tour

This is the shortest path from "I have never used NullRun" to
"I shipped an agent to production and it tripped a budget cap." It
mirrors the dashboard tour at `nullrun.io/onboarding` — same five
screens, same five CLI commands.

> **If you want to install first**, jump to [Install](install.md) and
> come back. This tour assumes `nullrun` is already installed and an
> API key is exported as `NULLRUN_API_KEY`.

## What you will build

A LangGraph agent that:

1. Calls `gpt-4o-mini` through the NullRun gate
2. Has a hard $0.50 budget per workflow
3. Trips the circuit breaker when it tries to call `send_email`
4. Recovers cleanly after you raise the budget

You will see each step land in the dashboard as a real audit row.

## Step 1 — Create an organization

If you do not already have one, open `nullrun.io/onboarding`,
pick a name ("Acme AI"), and click **Create**. The dashboard
provisions an `organization_id` and a default `policy_id` that
allows everything except destructive tools.

!!! note "What you see"
    On the dashboard home, a single card shows: organization name,
    default policy name (`Permissive`), and an "API keys" tile that
    is empty until step 2.

## Step 2 — Create an API key

In the dashboard:

1. Click **Settings → API keys**.
2. Click **+ New key**.
3. Name it `tour-agent` (or anything memorable).
4. Copy the `nr_live_…` public identifier and the HMAC secret.
   The secret is shown **once** — store it in your secrets manager
   immediately.

Export both in your shell:

```bash title="shell"
export NULLRUN_API_KEY="nr_live_xxxxxxxxxxxxxxxx"
export NULLRUN_HMAC_SECRET="hmac_xxxxxxxxxxxxxxxxxxxx"
```

!!! warning "Where the HMAC secret lives"
    The SDK pulls the HMAC secret via `POST /api/v1/auth/verify` on
    first use, then caches it in memory. Re-exporting the env var
    does NOT invalidate an existing cached secret — restart your
    process to pick up a new one.

## Step 3 — Wire up the agent

Create a file `tour_agent.py`:

```python title="tour_agent.py"
import os
import nullrun
from nullrun import init, protect, NullRunBudgetError
from langchain_openai import ChatOpenAI

init(api_key=os.environ["NULLRUN_API_KEY"])

llm = ChatOpenAI(model="gpt-4o-mini")

@protect
def ask(question: str) -> str:
    return llm.invoke(question).content

if __name__ == "__main__":
    for i in range(20):
        try:
            print(f"[{i}]", ask("Tell me a one-sentence joke."))
        except NullRunBudgetError as exc:
            print(f"[{i}] BLOCKED:", nullrun.format_user_message(exc))
            break
```

Run it:

```bash title="shell"
pip install "nullrun[langgraph]" langgraph langchain-openai
python tour_agent.py
```

You will see ~7–10 successful LLM calls, then
`BLOCKED: You've used all your support credits. Upgrade to keep chatting.`
(or whatever your catalog wording is).

## Step 4 — Watch the decisions

Open `nullrun.io/decisions` (or the dashboard **Decision History**
tab). You will see:

- One row per `@protect` call
- `decision = allow` for the first ~7–10 rows
- `decision = block` on the last row with `error_code = NR-B004`,
  `wire = BUDGET_HARD_BLOCKED`
- The **reason** column links to the budget snapshot at the time
  of the block

Each row is a `record_governance_audit_event` from the backend —
identical to what ships in your customer's audit trail.

## Step 5 — Trip a ToolBlock

Edit `tour_agent.py` and add a second protected function:

```python title="tour_agent.py"
@protect
def send_email(to: str, body: str) -> None:
    # Pretend SMTP call.
    print(f"SMTP → {to}: {body}")
```

Then call it from `__main__`:

```python title="tour_agent.py"
# After the loop:
try:
    send_email("test@example.com", "hi from the tour")
except nullrun.NullRunToolBlockedError as exc:
    print(f"BLOCKED:", nullrun.format_user_message(exc))
```

Run it again. The dashboard shows a `decision = block` row with
`error_code = NR-T001`, `wire = TOOL_BLOCKED`. The default
policy ships with `send_*` blocked.

To allow it, open **Policies → Default → Tool patterns** and
remove the `send_*` entry (or scope it to a different workflow).

## Step 6 — Raise the budget and try again

Back in the dashboard:

1. Open **Workflows → tour-agent → Settings**.
2. Change the budget to `$5.00` (500 cents).
3. Save.

Re-run `tour_agent.py`. The loop now completes all 20 calls. The
**Spend** tab shows ~$0.40 used (depending on token counts), and
the progress bar sits at ~8%.

## What next?

| You want to… | Open |
| --- | --- |
| Understand the gate in depth | [Concepts → Circuit breaker](../concepts/circuit-breaker.md) |
| Wire up multiple agents | [How-to → Run multiple agents](../how-to/multi-agent.md) |
| Add an approval flow for sensitive tools | [Concepts → Human approval](../concepts/human-approval.md) |
| Stream responses | [How-to → Stream responses](../how-to/streaming.md) |
| Deploy to production behind your gateway | [Configuration → Behaviour](configuration.md#behaviour) |

!!! tip "Where to send feedback"
    Email `support@nullrun.io` with the dashboard's
    **Help → Send feedback** form filled in. Include the workflow ID
    (top-right of any dashboard page) and the failing row's
    `decision_id`.
