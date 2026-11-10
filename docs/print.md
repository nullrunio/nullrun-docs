---
title: NullRun — printable documentation
description: The complete NullRun documentation in a single page, formatted for printing or saving as PDF.
search:
  exclude: true
---

# NullRun documentation

> **To print this page:** press **Ctrl + P** (Windows / Linux) or **⌘ + P** (macOS), or use the button below.
>
> <button class="nr-print-btn" type="button" onclick="window.print()" aria-label="Print this page">🖨 Print this page</button>
>
> **To save as PDF:** in the print dialog, choose *Save as PDF* (Chrome / Edge) or *Save as PostScript* → *PDF* (Safari) as the destination.

This single-page edition contains the full NullRun documentation
flattened for printing. Use it as an offline reference — the
source-of-truth remains [docs.nullrun.io](https://docs.nullrun.io).

---

## Table of contents

1. [Getting started](#1-getting-started)
    - [1.1 First agent in 15 minutes](#11-first-agent-in-15-minutes)
    - [1.2 5-minute tour](#12-5-minute-tour)
    - [1.3 Installation](#13-installation)
    - [1.4 Quickstart](#14-quickstart)
    - [1.5 Configuration](#15-configuration)
2. [Decision model](#2-decision-model)
    - [2.1 Circuit breaker](#21-circuit-breaker)
    - [2.2 Policies](#22-policies)
    - [2.3 Tool policies](#23-tool-policies)
    - [2.4 Sensitive tools](#24-sensitive-tools)
    - [2.5 API keys](#25-api-keys)
3. [Cost & safety](#3-cost-safety)
    - [3.1 Budgets](#31-budgets)
    - [3.2 Human approval](#32-human-approval)
4. [Runtime](#4-runtime)
    - [4.1 Workflow context](#41-workflow-context)
    - [4.2 Tracing](#42-tracing)
    - [4.3 Error handling](#43-error-handling)
    - [4.4 Control plane (WebSocket)](#44-control-plane-websocket)
    - [4.5 MCP servers (Action sources)](#45-mcp-servers-action-sources)
5. [Organization](#5-organization)
    - [5.1 Approvals (UI surface)](#51-approvals-ui-surface)
    - [5.2 Notifications](#52-notifications)
    - [5.3 Alerts](#53-alerts)
    - [5.4 Team](#54-team)
    - [5.5 Billing & Plan](#55-billing-plan)
    - [5.6 Organization](#56-organization)
    - [5.7 Profile settings](#57-profile-settings)
6. [How-to](#6-how-to)
    - [6.1 Protect a LangGraph agent](#61-protect-a-langgraph-agent)
    - [6.2 Use with OpenAI Agents](#62-use-with-openai-agents)
    - [6.3 Use CrewAI](#63-use-crewai)
    - [6.4 Use with FastAPI](#64-use-with-fastapi)
    - [6.5 LLM frameworks](#65-llm-frameworks)
    - [6.6 Set a hard cost cap](#66-set-a-hard-cost-cap)
    - [6.7 Run multiple agents](#67-run-multiple-agents)
    - [6.8 Multi-agent orchestration](#68-multi-agent-orchestration)
    - [6.9 Stream responses](#69-stream-responses)
    - [6.10 Manual cost / event tracking](#610-manual-cost-event-tracking)
    - [6.11 CI / CD integration](#611-ci-cd-integration)
7. [Reference](#7-reference)
    - [7.1 SDK API](#71-sdk-api)
    - [7.2 Decorators & context managers](#72-decorators-context-managers)
    - [7.3 HTTP API](#73-http-api)
    - [7.4 Error lookup](#74-error-lookup)
    - [7.5 Error codes](#75-error-codes)
    - [7.6 Tool catalog](#76-tool-catalog)
    - [7.7 Glossary](#77-glossary)
8. [Compliance](#8-compliance)
    - [8.1 Overview](#81-overview)
    - [8.2 Data handling & vendor review](#82-data-handling-vendor-review)
9. [Operations](#9-operations)
    - [9.1 Troubleshooting](#91-troubleshooting)
    - [9.2 Performance & limits](#92-performance-limits)
    - [9.3 Framework & ecosystem positioning](#93-framework-ecosystem-positioning)
    - [9.4 Changelog](#94-changelog)

---

# 1. Getting started


## 1.1 First agent in 15 minutes

This is the path from "I have an LLM app" to "NullRun is gating my spend and my tools".

### 1. Create a workspace and a workflow

Sign in at [nullrun.io](https://nullrun.io). The setup wizard walks through five steps: **Workspace**, **Workflow**, **API key**, **Connect**, **Ready**.

1. **Workspace** — name your workspace.
2. **Workflow** — name the workflow your agent runs as. The wizard creates the workflow, a **Budget Limit** policy of `$10` scoped to that workflow, and an API key bound to it.
3. **API key** — the key appears once. Copy it into your shell:

```bash title="shell"
export NULLRUN_API_KEY=nr_live_...
```

The signing secret is never shown again. The SDK fetches it from the gateway on first use.

You can create more keys later under **Access → API keys**. Each key is bound to one workflow.

<figure class="nr-shot">
  <img class="nr-shot__light" src="../assets/images/screenshots/api-key-new-light.png"
       alt="NullRun New API key dialog, with the workflow dropdown and key name field."
       loading="lazy" decoding="async">
  <img class="nr-shot__dark" src="../assets/images/screenshots/api-key-new-dark.png"
       alt="NullRun New API key dialog, with the workflow dropdown and key name field."
       loading="lazy" decoding="async">
  <figcaption class="nr-shot__caption">API keys · New key</figcaption>
</figure>

### 2. Install the SDK

```bash title="shell"
pip install nullrun
```

The plain `nullrun` package is enough. It depends on `httpx` and nothing else, and it hooks the providers and frameworks you already use. See [Install → What gets instrumented](#13-installation).

### 3. Wire NullRun into your code

#### A. You call the provider SDK directly

Decorate the function that calls the provider. The [Quickstart](#14-quickstart) has the full example.

`@protect` is the gate: it asks the gateway for a decision, and it stops the call when the answer is no. Cost tracking is separate — the SDK instruments the HTTP client and books the tokens on its own.

`with nullrun.guard():` catches the refusal, prints the message, and exits with code `1`. Use a plain `try` and `except` when your service has to stay up.

`init()` is optional. The first `@protect` call creates the runtime from `NULLRUN_API_KEY`. Call it when you want a missing key to fail at startup. See [Quickstart → Start the runtime yourself](#14-quickstart).

#### B. You use a framework

Auto-instrumentation covers the same ground. See [Use with LangGraph](#61-protect-a-langgraph-agent) and the other [framework how-tos](#65-llm-frameworks).

### 4. Set the budget

The wizard seeds a Budget Limit policy of `$10` for the new workflow. Open **Governance → Policies** to edit it, or to add another one.

| Use case | Starting cap |
|---|---|
| Personal experiment | `$5.00` (`500` cents) per period |
| Internal tool | `$20.00` (`2000` cents) per period |
| Customer-facing feature | `$100.00` (`10000` cents) per period, with alerts |

A Budget Limit policy has an **Enforcement mode**. `Hard` stops every call once the cap is reached. `Soft` lets calls through inside an overdraft cap.

The period window differs by plan. See [Budgets → Periods](#31-budgets).

### 5. Run it and watch the decisions

```bash title="shell"
python my_agent.py
```

Then open **Workflows → your workflow → Executions**. Every protected call gets a row. The **Result** column holds the gate verdict, and **Cost** holds what the call cost.

For the raw numbers, `GET /api/v1/orgs/{org_id}/status` returns the spend of the period, the cap, and what is left of it in one call. See [HTTP API → Budget and status](#73-http-api).

### 6. Tighten or loosen

1. **Block a tool** the agent should not touch — see [Tool policies](#23-tool-policies) and the starter list in the [Tool catalog](#76-tool-catalog).
2. **Ask a human first** on a sensitive action — see [Human approval](#32-human-approval).
3. **Let a long agent overspend on purpose** — see [Workflows → Chain context](#41-workflow-context).
4. **Forward every error to your monitoring** — see [Error handling](#43-error-handling).

### Next

- [5-minute tour → the control center end to end](#12-5-minute-tour)
- [Concepts → Circuit breaker](#21-circuit-breaker)
- [How-to → Run multiple agents](#67-run-multiple-agents)
- [How-to → Stream responses](#69-stream-responses)


## 1.2 5-minute tour

This is the shortest path from "I have never used NullRun" to "my agent stopped itself at the budget cap". Six screens, one script, one cap.

> **Install first?** Jump to [Install](#13-installation) and come back. This tour assumes the `nullrun` package is installed and `NULLRUN_API_KEY` is exported.

### What you will build

A small agent that:

1. Calls `gpt-4o-mini` through the NullRun gate
2. Runs on a workflow with a budget of `$10`
3. Books about two cents of spend in one run
4. Stops at the cap once you lower it to one cent

Every call lands in the control center.

### Step 1 — Set up the workspace

Open [nullrun.io/onboarding](https://nullrun.io/onboarding). The wizard walks through five steps: **Workspace**, **Workflow**, **API key**, **Connect**, **Ready**.

1. **Workspace** — name it.
2. **Workflow** — name it `tour-agent`. The wizard creates the workflow, a **Budget Limit** policy of `$10` scoped to it, and an API key bound to it.

### Step 2 — Create an API key

To use the key the wizard made, you can skip this step. To create another one:

1. In the sidebar, under **Access**, click **API keys**.
2. Click **New API key** in the top right.
3. In the dialog, pick the **Workflow** the key belongs to and name the key `tour-agent`. Pick an expiration: **Never**, **24 hours**, **7 days**, **30 days**, or **90 days**.
4. Click **Create** and copy the `nr_live_…` identifier.

<figure class="nr-shot">
  <img class="nr-shot__light" src="../assets/images/screenshots/api-keys-list-light.png"
       alt="API keys page showing the New key button highlighted in the top right."
       loading="lazy" decoding="async">
  <img class="nr-shot__dark" src="../assets/images/screenshots/api-keys-list-dark.png"
       alt="API keys page showing the New key button highlighted in the top right."
       loading="lazy" decoding="async">
  <figcaption class="nr-shot__caption">API keys · New key</figcaption>
</figure>

The control center shows the key once. The signing secret is never shown, and the SDK does not need it — it fetches the secret from the gateway on first use.

```bash title="shell"
export NULLRUN_API_KEY="nr_live_xxxxxxxxxxxxxxxx"
```

### Step 3 — Wire up the agent

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

### Step 4 — Watch the decisions

Open **Governance → Audit log**. You see:

- One row per protected call, in four columns: **Time**, **Decision**, **Rule**, **Actor**.
- The period presets **24h**, **7d**, **30d**, **90d**, and **All**, plus a **Custom** range. The page opens on **30d**.
- **Allow** on every row so far.

The audit log is a plan feature. Lite and Starter do not have it. A new workspace gets a 14-day Scale trial, so the audit log is there while the trial runs. After the trial the workspace keeps its Lite plan and loses the audit log. See [Billing → The Lite trial](#55-billing-plan).

<figure class="nr-shot">
  <img class="nr-shot__light" src="../assets/images/screenshots/audit-log-light.png"
       alt="Audit log page — Allow / Deny / Require approval filter chips and the events table."
       loading="lazy" decoding="async">
  <img class="nr-shot__dark" src="../assets/images/screenshots/audit-log-dark.png"
       alt="Audit log page — Allow / Deny / Require approval filter chips and the events table."
       loading="lazy" decoding="async">
  <figcaption class="nr-shot__caption">Governance · Audit log</figcaption>
</figure>

### Step 5 — Trip the cap

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

### Step 6 — Raise the cap

Edit the same policy and set **Max cost (USD/month)** to `5` (`$5.00`). Run the script once more. All thirty calls succeed.

The **Overview** tab of the workflow shows the spend against the cap.

### What next?

| You want to… | Open |
| --- | --- |
| Block a tool the agent must not touch | [Concepts → Tool policies](#23-tool-policies) |
| Ask a human to approve a sensitive action | [Concepts → Human approval](#32-human-approval) |
| Understand the gate in depth | [Concepts → Circuit breaker](#21-circuit-breaker) |
| Run several agents | [How-to → Run multiple agents](#67-run-multiple-agents) |
| Stream responses | [How-to → Stream responses](#69-stream-responses) |
| Tune the SDK | [Configuration → Behaviour](#15-configuration) |

!!! tip "Where to send feedback"
    Email `support@nullrun.io`. Include the workflow ID and the `decision_id` of the row that surprised you.


## 1.3 Installation

### Install the SDK

```bash title="shell"
pip install nullrun
```

The package needs Python 3.10 or newer. It depends on `httpx` and nothing else.

```bash title="shell"
python -c "from nullrun import protect; print('ok')"
```

### Create an API key

Sign in at [nullrun.io](https://nullrun.io). Open **Access → API keys** and click **New API key**. The dialog asks for a name, a workflow, and an expiration.

The key is enough. The SDK signs its requests with the key and fetches the matching signing secret from `POST /api/v1/auth/verify` on first use. Without a key the SDK raises `NullRunAuthenticationError` with the code `NR-C001`.

```bash title="shell"
export NULLRUN_API_KEY=nr_live_...
```

Set `NULLRUN_SECRET_KEY` yourself only if your secret manager already holds the signing secret.

### What gets instrumented

Instrumentation attaches when the runtime starts — at `init()`, or at the first `@protect` call if you never call `init()`. The SDK patches the HTTP client and each agent framework it recognises. A framework that is not installed is skipped.

| Package | What the SDK attaches |
| --- | --- |
| `httpx` | Token counting for every provider built on it |
| `requests` | Token counting through `Session.send` |
| `langchain-core` | Callback manager and chat model hooks |
| `openai-agents` | `Runner.run` and `Runner.run_sync` |
| `langgraph` | `Pregel.invoke`, `stream`, `ainvoke`, `astream` |
| `llama-index` | LLM chat-end and function-call events |
| `crewai` | `Crew.kickoff` and `kickoff_async` |
| `autogen` | `BaseChatAgent.on_messages` and the OpenAI chat client |

Provider traffic is recognised by host, not by package:

| Host | Provider |
| --- | --- |
| `api.openai.com` | OpenAI |
| `openai.azure.com` | Azure OpenAI |
| `api.anthropic.com` | Anthropic |
| `generativelanguage.googleapis.com` | Gemini |
| `api.cohere.ai` | Cohere |
| `api.mistral.ai` | Mistral |
| `bedrock-runtime.amazonaws.com` | Bedrock |

NullRun never imports a vendor package. Install the vendor package you already use.

### Frameworks

Install the framework next to the SDK. No extra is needed for any of them.

```bash title="shell"
pip install nullrun langgraph langchain-openai
pip install nullrun crewai
pip install nullrun openai-agents
```

### Optional extras

| Extra | Installs | When you need it |
| --- | --- | --- |
| `nullrun[websocket]` | `websockets` | Real-time workflow state push. Without it the SDK polls the gateway for state changes, and a kill or pause takes longer to reach the agent. |
| `nullrun[opentelemetry]` | `opentelemetry-api`, `opentelemetry-sdk` | Exporting spans to an OpenTelemetry collector. |
| `nullrun[dev]` | `websockets`, `pytest`, `pytest-asyncio`, `pytest-rerunfailures`, `pytest-xdist`, `pytest-cov`, `respx`, `coverage`, `httpx`, `mypy`, `ruff`, `langchain-core`, `fastapi`, `tomli` (Python 3.10 only) | Running the SDK test suite locally. |

```bash title="shell"
pip install "nullrun[websocket]"
```

### If the control center stays empty

The SDK logs one warning when `@protect` has run 50 times and the SDK has seen no LLM call. The gate is enforced, but no cost is booked. The usual causes are a raw `httpx` client outside the instrumented surface, a custom transport, or a framework that is not on the list above.

### Next

- [Quickstart → your first gated call](#14-quickstart)
- [Configuration → every setting](#15-configuration)
- [Reference → init](#71-sdk-api)


## 1.4 Quickstart

Install the SDK, export an API key, decorate one function.

### 1. Install

```bash title="shell"
pip install nullrun
```

### 2. Export an API key

Create a key in the control center under **Access → API keys**. Every key is bound to one workflow.

```bash title="shell"
export NULLRUN_API_KEY=nr_live_...
```

### 3. Decorate one function

`@protect` is the only decorator. It works on sync functions and on async functions.

```python title="app.py"
import nullrun
from openai import OpenAI
from nullrun import protect

client = OpenAI()


@protect
def answer(prompt: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    with nullrun.guard():
        print(answer("What does NullRun do?"))
```

`import nullrun` gives you `nullrun.guard()`. `from nullrun import protect` gives you the decorator.

### 4. Run it

```bash title="shell"
python app.py
```

### What the gate does

`@protect` sends a gate request when the protected function is called. The gateway checks:

- the budget of the workflow your API key is bound to
- the tool rules that match the call
- the rate limit

If the gateway allows the call, the function body runs. The SDK then tracks the input tokens, the output tokens, and the cost.

### What a refusal looks like

`with nullrun.guard():` catches every `NullRunError`. It writes the user-facing message and a developer report to stderr. The report carries the error code, the stage that failed, the endpoint, the reason, and the fix. The process exits with code `1`. A kill signal propagates instead of being caught.

```
You've reached the usage limit for this conversation. Please try again later.
```

### Start the runtime yourself

`init()` is optional. The first `@protect` call creates the runtime from `NULLRUN_API_KEY`.

```python title="app.py"
import nullrun

nullrun.init()
```

Call it when you want a missing key to fail at startup rather than at the first request. A missing key raises `NullRunAuthenticationError` with the code `NR-C001`. `init()` also registers a clean shutdown on process exit.

### What gets tracked

- LLM tokens in and out
- Cost per call
- Latency
- Tool calls made through an instrumented framework

### Next

- [Install → optional extras](#13-installation)
- [First agent → the full walkthrough](#11-first-agent-in-15-minutes)
- [Configuration → every setting](#15-configuration)
- [Troubleshooting → every refusal and its fix](#91-troubleshooting)
- [Concepts → Circuit breaker](#21-circuit-breaker)
- [Concepts → Control plane](#44-control-plane-websocket)
- [Concepts → Error handling](#43-error-handling)
- [How-to → Set a hard cost cap](#66-set-a-hard-cost-cap)


## 1.5 Configuration

The Python SDK reads its settings from environment variables. Only `NULLRUN_API_KEY` is required. The gateway is operated by the NullRun team and exposes no user-facing runtime flags.

### Connection

| Variable | Purpose | Default |
| --- | --- | --- |
| `NULLRUN_API_KEY` | API key from the control center (`nr_live_...`). The SDK signs every gateway request with it. | unset — required |
| `NULLRUN_SECRET_KEY` | Signing secret for that key. The SDK fetches it from `POST /api/v1/auth/verify` when this variable is unset. | unset |
| `NULLRUN_API_URL` | Base URL of the gateway. Point it at a self-hosted gateway only if you run one. | `https://api.nullrun.io` |
| `NULLRUN_ENV` | Deployment label. `production` or `prod` marks the process as production. | unset |
| `NULLRUN_REQUEST_TIMEOUT` | Seconds the SDK waits for one gateway request. | `30` |

The SDK treats a process as production when `NULLRUN_ENV` is `production` or `prod`, or when the gateway URL is `api.nullrun.io`. A loopback host is never production, whatever `NULLRUN_ENV` says. Production arms the guards on the development bypasses below.

### Gate and approvals

| Variable | Purpose | Default |
| --- | --- | --- |
| `NULLRUN_TRANSPORT` | Control-plane transport: `ws` for WebSocket push, `http` for polling. | `ws` |
| `NULLRUN_APPROVAL_TIMEOUT_SECONDS` | Seconds the SDK waits for a human approval decision. It is the fallback when the gateway sends no timeout of its own. | `300` |
| `NULLRUN_V3_TRACK_DISABLE` | Set to `1` to send every tracked event through the batch path instead of the single-event path. Use it on a gateway that does not settle per-execution reservations. | unset |

### Event delivery

| Variable | Purpose | Default |
| --- | --- | --- |
| `NULLRUN_BATCH_SIZE` | Number of tracked events the SDK sends per flush. | `50` |
| `NULLRUN_FLUSH_INTERVAL_MS` | Milliseconds between flushes of tracked events. | `5000` |
| `NULLRUN_MAX_BATCH_ATTEMPTS` | How many times the SDK sends one batch before it moves that batch to the dead-letter file. | `10` |
| `NULLRUN_MAX_BISECT_REQUESTS` | How many requests the SDK may send while it splits a batch the gateway rejected. | `64` |
| `NULLRUN_RETRY_AFTER_CEILING` | Seconds the SDK waits when the gateway answers `429` with a `Retry-After` header. A `Retry-After` above this ceiling is not retried in the current cycle. | `60` |
| `NULLRUN_MAX_RESPONSE_BYTES` | Largest HTTP response body the SDK reads for token counting. A bigger body is delivered to your code but not counted. | `16777216` (16 MiB) |

### Write-ahead log

The SDK keeps events it could not deliver in a write-ahead log on disk. The log holds the events the gateway has not accepted yet, so a crash or a network outage does not lose spend that already happened.

| Variable | Purpose | Default |
| --- | --- | --- |
| `NULLRUN_WAL_PATH` | Path of the write-ahead log. Give every runtime its own path. | `<tempdir>/nullrun-<user>-<key-digest>.wal` |
| `NULLRUN_WAL_MAX_BYTES` | Size at which the SDK rotates the write-ahead log. | `67108864` (64 MiB) |
| `NULLRUN_WAL_LOCK_TIMEOUT_MS` | Milliseconds the SDK waits for the write-ahead log lock before it gives up. | `5000` |
| `NULLRUN_DLQ_MAX_BYTES` | Size at which the SDK stops adding to the dead-letter file. | `67108864` (64 MiB) |
| `NULLRUN_DLQ_HOLDOVER_MAX_EVENTS` | Number of dead-letter entries the SDK keeps in memory as an index. The file itself keeps every row. | `10000` |

The default write-ahead log path carries a digest of the API key, not the key itself. Two API keys on one machine never share a file.

### Edge node

| Variable | Purpose | Default |
| --- | --- | --- |
| `NULLRUN_EDGE_URL` | Base URL of an edge node that enforces the gate next to the agent. | unset |
| `NULLRUN_EDGE_LEASE_ID` | Lease the edge node uses for this runtime. Required when `NULLRUN_EDGE_URL` is set. | unset |
| `NULLRUN_EDGE_TOKEN` | Token the edge node authenticates with. Required when `NULLRUN_EDGE_URL` is set. | unset |
| `NULLRUN_EDGE_TIMEOUT_SECONDS` | Seconds the SDK waits for one edge node request. | `2` |
| `NULLRUN_EDGE_MAX_RETRIES` | How many times the SDK retries a failed edge node request. | `2` |

`NULLRUN_API_KEY` is required as well when `NULLRUN_EDGE_URL` is set. The edge node checks the caller's key against the fingerprint inside the grant.

### TLS

| Variable | Purpose | Default |
| --- | --- | --- |
| `NULLRUN_TLS_CA_CERT` | Path to a custom CA certificate the SDK trusts when it reaches the gateway. | unset |
| `NULLRUN_TLS_CLIENT_CERT` | Path to a client certificate the SDK presents to the gateway. | unset |
| `NULLRUN_TLS_CLIENT_KEY` | Path to the key of that client certificate. | unset |

### Malformed values

A value that is not a number is ignored. `NULLRUN_BATCH_SIZE`, `NULLRUN_FLUSH_INTERVAL_MS`, `NULLRUN_EDGE_TIMEOUT_SECONDS`, and `NULLRUN_EDGE_MAX_RETRIES` log a warning that names the variable. The other numeric variables fall back to their default silently. `NULLRUN_MAX_BATCH_ATTEMPTS` and `NULLRUN_MAX_BISECT_REQUESTS` must be whole numbers.

### Development and test bypasses

!!! danger "A production deployment must not set these"
    The two variables below switch off a safety check. They exist for local development and for test suites. A production deployment must not set them, and a test that only passes with them set is a defect in the gate, not in the test.

| Variable | Effect |
| --- | --- |
| `NULLRUN_SKIP_BUDGET_CHECK=1` | Skips the budget pre-flight on every protected call in the process. The call is still tracked and billed, but nothing is reserved against the budget. |
| `NULLRUN_SENSITIVE_FAIL_OPEN=1` | Lets a protected tool run when the policy engine cannot be reached. Only tools the operator classified as fail-open-allowed are affected. The set of classified tools is empty until you call `register_fail_open_tools` on the runtime, so the switch alone opens nothing. |

Each one needs a second variable that acknowledges the risk:

| Variable | Effect |
| --- | --- |
| `NULLRUN_ALLOW_SKIP_BUDGET_CHECK=1` | Acknowledges `NULLRUN_SKIP_BUDGET_CHECK=1` in production. |
| `NULLRUN_ALLOW_SENSITIVE_FAIL_OPEN=1` | Acknowledges `NULLRUN_SENSITIVE_FAIL_OPEN=1` in production. |

The SDK refuses a bypass that is armed in production without its acknowledgement. `NULLRUN_SKIP_BUDGET_CHECK=1` raises `NullRunInfrastructureError` with the code `NR-S001`. `NULLRUN_SENSITIVE_FAIL_OPEN=1` is ignored, and the tools stay fail-closed.

### Behaviour

The control plane carries workflow state — kill, pause, resume. The SDK receives it over a WebSocket push channel. It falls back to polling the gateway every second when the WebSocket endpoint is blocked, when the `websockets` package is not installed, or when `NULLRUN_TRANSPORT=http` selects the poller.

The edge settings change where the gate runs. With `NULLRUN_EDGE_URL` set, the gate request goes to the edge node instead of the cloud. Cost events still go to the cloud. An unreachable edge node refuses the call. The SDK does not fall back to the cloud, because a silent fallback would let the agent keep spending with no grant in force.

`NULLRUN_USE_GRPC` is reserved. Setting it makes `init()` raise a `RuntimeError`, because the gRPC transport is not implemented.

### See also

- [HTTP API](#73-http-api)
- [Install → optional extras](#13-installation)
- [Concepts → Control plane](#44-control-plane-websocket)
- [Concepts → Circuit breaker](#21-circuit-breaker)


# 2. Decision model


## 2.1 Circuit breaker

The SDK ships a client-side circuit breaker in the transport layer. It
watches the event flush the SDK makes to the gateway. After a run of
failed flushes it opens and stops sending, so an unreachable gateway
does not turn into a hang. It closes again after a cooldown.

A policy refusal and a breaker trip are different things:

- A **policy refusal** is the gateway answering "no". The gate
  evaluated your rules and blocked the call.
- A **breaker trip** is the SDK noticing that the gateway is not
  answering at all.

### States

| State | What happens |
|---|---|
| **Closed** | The flush goes out normally. A transport failure raises the failure count. A success resets it. |
| **Open** | The flush is skipped. The events stay queued and the SDK retries them after the cooldown. |
| **Half-open** | The breaker lets one probe through. A success closes it. Another failure opens it again. |

The breaker keeps its state in the process that runs it, so two
processes run two breakers.

### When it opens

The breaker opens after a run of consecutive transport failures: a
timeout, a refused connection, a 5xx. The threshold is the failed-flush
limit, 10 by default.

The half-open probe waits 30 seconds, plus a random delay of up to 5
seconds, so two processes do not probe at the same instant. One probe
runs at a time.

While the breaker is open the SDK keeps the pending events and retries
them on a later flush. The agent keeps running.

### What it raises

Nothing into your code. The breaker sits on the event flush, in a
background thread. When it is open, the SDK logs a warning and moves on.

`BreakerError` and `BreakerTransportError` are the breaker's own
exception types. They stay inside the SDK, so neither
`except NullRunError` nor `except BreakerTransportError` in your code
sees one.

One breaker error does reach you, and it happens at start-up rather than
during a run: an API URL on plain HTTP against a host that is not
localhost raises `InsecureTransportError`.

### What it does not do

The breaker does not sit on the gate path. It guards the event flush,
not the policy decision. A protected call is never blocked by it.

When the gateway cannot be reached, the gate path fails closed on its
own. A network failure raises `NullRunBlockedException` with `NR-B001`,
a gateway 5xx raises `NullRunBlockedException` with `NR-B002`, and a
rejected key raises `NullRunAuthError` with `NR-A003`. The protected body
does not run in any of the three cases. See
[Policies → Fail closed](#22-policies).

The gateway keeps a per-workflow breaker of its own. When breaker
enforcement is on, an open workflow breaker refuses the call with HTTP
403 `CIRCUIT_BREAKER_TRIPPED`, which the SDK raises as
`NullRunBlockedException`.

The breaker never relaxes enforcement. A tool block, a budget refusal
and a rate-limit refusal are answers from the gateway, and the SDK
raises them whatever state the breaker is in.

### See also

- [Policies](#22-policies) — the rules the gate enforces
- [Error handling](#43-error-handling) — how a refusal reaches your code
- [Troubleshooting](#91-troubleshooting) — common "why is my agent
  blocked?" questions


## 2.2 Policies

A **policy** is a rule attached to your organization or to a single
workflow. In the control center they live under **Governance → Policies**.

### What you see in the control center

The **Policies** page lists every policy in your org. Each row shows:

- **Name** — what you set when you created the policy
- **Type** — what the policy caps
- **Config** — a preview of the cap or the pattern
- **Scope** — the whole org, or one workflow
- **Active** — a toggle that turns the policy on and off without
  deleting it
- **Threshold** — the effective cap the policy contributes

Click a policy to edit it. A change applies to the next gate call.

### The three policy types

| Type | Wire name | What it controls | Example value |
|---|---|---|---|
| **BudgetLimit** | `budget_limit` | Maximum spend per period | `5000` ($50.00) |
| **RateLimit** | `rate_limit` | Maximum calls per minute | `60` (one call per second, sustained) |
| **ToolBlock** | `tool_block` | Tools the agent must not call | `["send_*", "db.drop", "stripe.charge"]` |

Each type carries a JSON config payload. The pattern syntax inside a
`ToolBlock` config is on [Tool policies](#23-tool-policies).

### BudgetLimit — extra fields

A `BudgetLimit` policy can carry these optional fields at the top level of
the body:

| Field | Default | What it does |
|---|---|---|
| `enforcement_mode` | `"Hard"` | `Hard` blocks on budget exceeded. `Soft` allows a bounded overdraft when an active chain is present. |
| `max_overdraft_cents` | `0` | Maximum overdraft in cents. The cent cap and the percent cap both apply — the lower one wins. |
| `max_overdraft_percent` | `0` | Maximum overdraft as a percentage of the budget. |
| `max_chain_duration_seconds` | `3600` | Stored on the policy. The gate ends a chain after one hour and does not read this field. |

The gate reads these fields from every applicable `BudgetLimit` and
uses **most-restrictive-wins**: `enforcement_mode` (Hard beats
Soft), `max_overdraft_cents` (min), `max_overdraft_percent` (min).

`enforcement_mode`, `max_overdraft_cents` and `max_overdraft_percent` are
BudgetLimit-only. The server refuses them with HTTP 422 when you create
a `RateLimit` or `ToolBlock` policy.

`BudgetLimit` also reads `consume_epsilon_cents` from its config. It
is the tolerance between the amount reserved for a call and the amount
the call is charged. It defaults to 1 cent, and the smallest value
across the applicable policies wins.

#### Soft mode requirements

Soft mode needs all three of these:

1. The policy uses `enforcement_mode = Soft` and is scoped to a
   **workflow**. The server refuses Soft mode on an
   organization-scope policy with HTTP 422.
2. An **active chain** exists — declared with `with chain(...)`.
3. The projected cost stays inside both `max_overdraft_cents` and
   `max_overdraft_percent`.

If one of the three is missing, the budget behaves as Hard. Parallel
chains on one organization share a single overdraft allowance, so
concurrency does not multiply the cap.

A chain ends on the first of: `op="end"`, five minutes without a gate
call, or one hour of chain lifetime.

### Aggregation

When two applicable policies disagree, the engine takes the **most
restrictive** numeric cap and the **union** of the tool patterns.

| Field | If two policies disagree |
|---|---|
| `budget_cents` | The smaller org-scope number wins, and the smaller workflow-scope number wins. The two caps stay apart because each is measured against its own counter. |
| `max_calls_per_minute` | The smaller number wins, per scope. |
| `enforcement_mode` | `Hard` beats `Soft` |
| `max_overdraft_cents` | The smaller number wins |
| `max_overdraft_percent` | The smaller number wins |
| `consume_epsilon_cents` | The smaller number wins |
| `tool_pattern` / `blocked_tools` / `tools` | Both lists merge — a tool blocked anywhere is blocked everywhere |

You cannot un-block a tool that another scope blocks. There is no
"allow" rule that overrides a "block".

A `ToolBlock` row that carries `parameter_conditions` blocks only when
the pattern matches **and** the condition holds. Its patterns stay out
of the unconditional pattern list.

### Org-level vs workflow-level

A policy has one of two scopes:

- **Organization** — applies to every workflow in your organization.
  Use it for rules like "all our agents must block `db.drop`".
- **Workflow** — applies to one workflow. Use it for rules like
  "this agent gets $500 per period".

Both scopes apply together. There is no override. The **Policies** tab
on a workflow page shows the merged set under **Effective controls**.

### Templates

The control center ships **templates** — pre-built policies for common
patterns:

1. On the **Policies** page, open **Templates**.
2. Pick a template.
3. Click **Activate**.

A template materialises as a real policy in your org. Activating it
again turns it off.

### Plan gating

| Feature | Available on |
|---|---|
| `BudgetLimit` policies | All plans |
| `RateLimit` policies | All plans |
| `ToolBlock` policies | All plans |
| Approval rules | Growth+ |
| Audit log | Growth+ |

Policies and approval rules share one quota per organization:

| Plan | Policies and approval rules |
|---|---|
| Lite | 3 |
| Starter | 10 |
| Growth | 25 |
| Scale | 150 |
| Enterprise | Unlimited |

If you try to use a feature your plan does not include, the control center
shows it greyed out with an **Upgrade** link, and the server refuses
the change.

### Fail closed

Every check on the enforcement path **refuses** when it cannot be
evaluated. A refusal is a refusal, not a pass.

| Situation | Result |
|---|---|
| The gateway cannot be reached | The protected body does not run. A network failure raises `NullRunBlockedException` with `NR-B001`, a gateway 5xx raises `NullRunBlockedException` with `NR-B002`, and a rejected key raises `NullRunAuthError` with `NR-A003`. |
| The rate-limit store cannot be reached | The call is refused with HTTP 503 `RATE_LIMIT_REDIS_UNAVAILABLE`. |
| The budget store cannot be reached | The call is refused with HTTP 402 `BUDGET_REDIS_UNAVAILABLE`. |
| A `ToolBlock` policy cannot be evaluated at the gate | The call is refused with HTTP 403 `TOOL_BLOCKED`. |
| A `ToolBlock` policy cannot be evaluated at the track backstop | The call is refused with HTTP 503 `TOOL_BLOCKED_BACKSTOP_UNAVAILABLE`. |

The SDK's own circuit breaker is the single local exception. After
repeated transport failures it stops calling the gateway and keeps
the pending work on disk. See
[Circuit breaker](#21-circuit-breaker).

The rate limiter keeps two buckets: one per key and one per
organization. Both can refuse on their own, and both read the same
store, so a store outage refuses with 503
`RATE_LIMIT_REDIS_UNAVAILABLE`.

### Approval rules — separate from ToolBlock

Approval rules are not a `ToolBlock` policy with an
`action = require_approval` field. They are a separate rule object
with `tool_patterns`, a projected-cost threshold, a typed
`BusinessImpact` predicate and operational metadata.

When a rule fires, the gate returns `decision = "require_approval"`
and the SDK parks until the operator clicks Approve or Deny. See
[Sensitive tools](#24-sensitive-tools) for how to choose between the
two, and [Human approval](#32-human-approval) for the approval flow.

### How to create one

1. **Governance → Policies → New policy**.
2. Pick the type (**Budget**, **Rate limit** or **Tool block**).
3. Pick the scope (**Organization** or one **Workflow**).
4. Fill in the config. The control center validates the JSON and shows the
   errors, so you can fix them.
5. Save. The policy is active immediately.

<figure class="nr-shot">
  <img class="nr-shot__light" src="../assets/images/screenshots/policies-list-light.png"
       alt="Policies list with the New policy button highlighted in the top right."
       loading="lazy" decoding="async">
  <img class="nr-shot__dark" src="../assets/images/screenshots/policies-list-dark.png"
       alt="Policies list with the New policy button highlighted in the top right."
       loading="lazy" decoding="async">
  <figcaption class="nr-shot__caption">Governance · Policies · New policy</figcaption>
</figure>

To test a policy, scope it to one workflow. The **Policies** tab of
that workflow shows the merged result.

### What gets logged

On Growth and above, every policy decision lands in **Governance →
Audit log**. Filter by decision (`allow`, `deny`, `require_approval`),
event type, actor and time window.

Lite and Starter do not include the audit log, so no decision rows are
written for them.

The audit log answers "why did my agent stop working at 14:32?".
Pair it with [Traces](#42-tracing) to see the request behind the
decision.

### See also

- [Tool policies](#23-tool-policies) — the `ToolBlock` pattern rules
- [Budgets](#31-budgets) — how a `BudgetLimit` interacts with the
  period rollover
- [Sensitive tools](#24-sensitive-tools) — blocking a tool against
  asking a human
- [Human approval](#32-human-approval) — rules that produce
  `require_approval`
- [Workflows](#41-workflow-context) — where the merged policy applies


## 2.3 Tool policies

A `ToolBlock` policy blocks tool calls by name. It is one of three
policy types — see [Policies](#22-policies) for the general overview.
This page is the reference for the pattern language and for the config
keys.

### What a tool name looks like

The agent calls tools by name, and the gate matches the canonical name.
Three shapes exist:

| Type | Format | Example |
|---|---|---|
| Built-in tool | lowercase string | `bash`, `file_write`, `execute_code` |
| MCP tool | `mcp://{server}/{tool}` | `mcp://filesystem/read` |
| Custom tool | `custom:{name}` | `custom:my_tool` |

A built-in name is lowercase ASCII letters, digits, `_` and `-`, up to
64 characters. The server part of an MCP name follows the same rule,
and the tool part may contain slashes. A custom name is non-empty and
at most 64 characters.

The matcher sees the name and nothing else. A rule is about which tool
runs, not what it is called with.

### Pattern syntax

`*` is the only metacharacter. `|` separates alternatives.

| Pattern | Matches | Does not match |
|---|---|---|
| `stripe.charge` | exactly `stripe.charge` | `execute_stripe.charge` |
| `send_*` | every name starting with `send_` | `resend_email` |
| `bash.*` | `bash`, `bash.foo`, `bash.foo.bar` | `bashful` |
| `*.drop_*` | `s3.drop_table` | `s3.execute_drop` |
| `bash\|sh` | `bash` or `sh` | `bashful` |
| `*` | every tool | — |

The rules behind the table:

- A pattern with no `*` is an **exact match**. It is never a substring
  match.
- A pattern with **one** `*` is an anchored prefix and/or suffix.
  `db.drop_*` matches `db.drop_table` and nothing else.
- A pattern with **two or more** `*` matches when every literal segment
  appears in the name, in order. The start stays anchored when the
  pattern does not begin with `*`, and the end when it does not end
  with `*`.
- `prefix.*` matches the bare prefix as well as its dotted
  continuations, so one pattern covers a whole namespace.
- `|` splits a pattern into alternatives. Each alternative is evaluated
  on its own.
- `**` matches nothing. `?` is a literal character, not a
  single-character wildcard.
- An empty pattern matches nothing.
- Matching is **case-sensitive**. Tool names are canonical lowercase,
  so `BASH` does not match `bash`.

Each entry is capped at **4096 bytes**. The cap bounds the work the
matcher does on every gate call.

### The config

A ToolBlock policy carries its patterns under one of three keys. The
three join the same list:

| Key | Value |
|---|---|
| `tool_pattern` | An array of pattern strings |
| `blocked_tools` | An array of pattern strings |
| `tools` | An array of pattern strings |

A fourth key, `parameter_conditions`, adds an argument-level
condition. Such a row blocks only when the pattern matches **and** the
condition holds, and its patterns stay out of the unconditional pattern
list. The control center offers two modes for it: **Any matching call** and
**Match specific parameters**.

### What a block does

ToolBlock always blocks. A `ToolBlock` policy has no soft mode, and
the server refuses an `enforcement_mode` on it with HTTP 422.

If the gate cannot evaluate the check, the call is refused with HTTP
403 `TOOL_BLOCKED` and the SDK raises `NullRunToolBlockedError`
(`error_code = "NR-T001"`). The protected body does not run. See
[Policies → Fail closed](#22-policies).

To put a human in the loop instead of blocking, use an approval rule.
See [Human approval](#32-human-approval).

### A worked example

Suppose the agent has these tools: `tavily_search`, `send_email`,
`db.write`, `db.drop`, `stripe.charge`, `read_file`.

You want to allow the read-only tools and the normal database write,
and to block the destructive ones:

```json title="tool_block_policy.json"
{
  "name": "Block destructive tools",
  "policy_type": "tool_block",
  "scope": "org",
  "config": {
    "tool_pattern": ["db.drop", "stripe.charge"]
  }
}
```

`policy_type` takes `budget_limit`, `rate_limit` or `tool_block`.
`scope` takes `org` or `workflow`. A workflow-scoped policy also
carries `workflow_id`.

The stored config is an array of patterns. The control center's **Tool
pattern** field is a single text box, so it writes one element and
separates the alternatives with `|`:

```json
{
  "tool_pattern": ["db.drop|stripe.charge"]
}
```

Both forms block the same set of tools.

### Validation at policy creation

The server rejects a malformed ToolBlock config with HTTP **422** and
the wire code `VALIDATION_FAILED`:

| Rejected | Why |
|---|---|
| A bare string instead of an array | `"tool_pattern": "send_*"` must be `"tool_pattern": ["send_*"]` |
| The plural key `tool_patterns` | The canonical key is singular: `tool_pattern` |
| An unknown key, such as `block_tools` | A typo would otherwise create a rule that blocks nothing |
| An empty pattern, or an empty config | A rule that blocks nothing |
| `parameter_conditions` with no tool pattern | The condition narrows an existing tool scope, it does not define one |
| An entry over 4096 bytes | The per-entry byte cap |
| A pattern containing control characters | Remove `\n`, `\r`, `\t` |

### Plan gating

`ToolBlock` policies are available on every plan. They draw on the
same per-organization quota as every other policy and as approval
rules — see [Policies → Plan gating](#22-policies).

**Approval rules** are a separate feature and are gated on Growth+.

### How to debug a block you didn't expect

If the agent reports `error_code = "NR-T001"` (wire `TOOL_BLOCKED`) on
a call you think should be allowed:

1. Open the workflow and go to the **Policies** tab. The **Effective
   controls** card shows every ToolBlock pattern that could match.
2. Open the policy in the editor. The **Will match** line lists the
   tool names a pattern covers.
3. Open **Governance → Audit log** and filter by `decision = deny`. The
   event detail has a **Matched rule** field that names the pattern
   that fired.
4. If a pattern is too broad, narrow it in the editor.
5. To take a rule out of service, turn the policy's **Active** toggle
   off. The policy stays in the list.

### See also

- [Policies](#22-policies) — the control center view, the aggregation rules
  and the fail-closed table
- [Sensitive tools](#24-sensitive-tools) — when to block and when to ask
  a human
- [Tool catalog](#76-tool-catalog) — common tool names
  with risk ratings
- [Human approval](#32-human-approval) — the approval-rule path,
  distinct from ToolBlock


## 2.4 Sensitive tools

A **sensitive tool** is one that should never run without a human
paying attention. Sending an email, moving money, deleting a record —
these have consequences the agent cannot easily undo.

The SDK keeps a built-in set of sensitive tool names — `stripe.charge`,
`send_email`, `db.delete` and similar — and you can add your own with
`runtime.register_sensitive_tools(...)`. The set classifies names. It
blocks nothing on its own. A tool that must not run is stopped by a
server-side rule, and the gate evaluates that rule on every protected
call.

### Two mechanisms

| Mechanism | Question it answers | Outcome |
|---|---|---|
| **[ToolBlock policy](#23-tool-policies)** | "May this tool run at all?" | The call is blocked. Always hard. |
| **[Approval rule](#32-human-approval)** | "May this tool run this time?" | The call parks until a human approves. |

Use a ToolBlock policy for a hard rule such as "never call `bash`". Use
an approval rule when the answer depends on the call's arguments, such
as "refunds over $500 need approval".

A ToolBlock policy matches the tool name alone. It cannot tell two
calls to the same tool apart, so it over-blocks when the arguments
matter.

An approval rule matches tool patterns and adds a typed predicate over
the call's arguments. When it fires, the gate returns
`require_approval` and the SDK parks until the operator clicks Approve
or Deny. The grant is bound to a SHA-256 digest of the exact payload,
so a changed amount or changed arguments after the approval is refused.
See [Human approval → Typed predicates](#32-human-approval).

### What a rule cannot see

A rule matches on the canonical tool name. It does not read:

- the prompt content or the agent's intent
- the tool's runtime sandbox — that is your infrastructure's job

Two features read the arguments when you need that:

- An **approval rule** carries a typed predicate over the call's
  arguments. See
  [Human approval → Typed predicates](#32-human-approval).
- A **ToolBlock row** can carry `parameter_conditions`. Such a row
  blocks only when the pattern matches **and** the condition holds.
  See [Tool policies](#23-tool-policies).

### Recommended starter patterns

The exact name comes from your MCP server or framework integration.
See the
[tool catalog](#76-tool-catalog)
for the maintained list with risk ratings.

| Category | Pattern examples |
|---|---|
| Money | `mcp://payments/refund*`, `mcp://stripe/charge`, `mcp://stripe/refund` |
| Email and messaging | `mcp://gmail/send`, `mcp://slack/post`, `send_email` |
| Database destructive | `mcp://postgres/drop_table`, `mcp://postgres/delete_row`, `execute_sql` |
| External API writes | `mcp://*/post`, `mcp://*/put`, `mcp://*/delete` |
| Files and storage | `mcp://s3/delete`, `file_delete`, `bash` |
| Admin | `mcp://admin/delete_user`, `mcp://admin/disable_user` |

### Where to write the rule

1. Go to **Governance → Policies → New policy**.
2. Under **What kind of policy?** pick **Tool block**.
3. Enter the pattern in the **Tool pattern** field.
4. Under **Where does this apply?** pick the scope — the whole
   organization, or one workflow.

The control center shows the canonical tool name for every framework
integration, and the **Will match** line tells you which names the
pattern covers. The pattern syntax is on
[Tool policies](#23-tool-policies).

Patterns **union** across every applicable policy — every pattern that
matches fires. See [Policies → Aggregation](#22-policies).

### Audit trail

A blocked sensitive tool lands in **Governance → Audit log** with the
decision `deny`, the reason code `TOOL_BLOCKED`, the pattern that
matched, the policy that matched and the tool name. The audit log is a
Growth+ feature, so Lite and Starter write no rows. The log is
hash-chained — see
[Error handling → Audit trail](#43-error-handling).

For a sensitive tool you want to allow after human review, pair the
approval rule with the ToolBlock rule rather than dropping it from the
blocking surface. The approval row carries its own audit trail, and
the digest binds the grant to the exact payload the agent sent.

### See also

- [Tool policies](#23-tool-policies) — the pattern syntax
- [Tool catalog](#76-tool-catalog) — recommended
  patterns with risk ratings
- [Human approval](#32-human-approval) — the safer alternative to
  removing a ToolBlock rule
- [Decorators and context managers](#72-decorators-context-managers) — the
  `@protect` decorator and the payload it sends


## 2.5 API keys

An **API key** authenticates your code with the NullRun gateway. It
identifies one workflow, and it comes with a second secret that signs
every request.

### Where you see it

API keys live under **Access → API keys**. The usage strip at the top
of the page shows how many keys your organization has against your
plan's cap.

| Plan | Keys |
|---|---|
| Lite | 10 |
| Starter | 15 |
| Growth | 100 |
| Scale | 350 |
| Enterprise | Unlimited |

The cap is enforced by the server. Creating a key past the cap is
refused with HTTP 422 and the slug `plan_limit_exceeded`.

### How to create a key

1. **Access → API keys → New key**.
2. Give the key a **name**. It shows up in the API keys list.
3. Pick the **workflow** the key belongs to. A key belongs to exactly
   one workflow, and the gateway uses that binding to apply the right
   policies. The server refuses a key with no workflow, and refuses a
   workflow that belongs to another organization.
4. Pick an **expiration**: **Never**, **24 hours**, **7 days**,
   **30 days**, or **90 days**. A key with no expiration works until
   you revoke it.
5. Click **Create Key**.

The control center shows the key value **once**. Copy it into your secret
manager immediately.

<figure class="nr-shot">
  <img class="nr-shot__light" src="../assets/images/screenshots/api-keys-list-light.png"
       alt="API keys list with the New key button highlighted in the top right."
       loading="lazy" decoding="async">
  <img class="nr-shot__dark" src="../assets/images/screenshots/api-keys-list-dark.png"
       alt="API keys list with the New key button highlighted in the top right."
       loading="lazy" decoding="async">
  <figcaption class="nr-shot__caption">API keys · New key</figcaption>
</figure>

<figure class="nr-shot">
  <img class="nr-shot__light" src="../assets/images/screenshots/api-key-new-light.png"
       alt="New API key dialog open — Key name field, Workflow dropdown, Create button."
       loading="lazy" decoding="async">
  <img class="nr-shot__dark" src="../assets/images/screenshots/api-key-new-dark.png"
       alt="New API key dialog open — Key name field, Workflow dropdown, Create button."
       loading="lazy" decoding="async">
  <figcaption class="nr-shot__caption">API keys · New key dialog</figcaption>
</figure>

### What a key is made of

| Part | What it is |
|---|---|
| **Key** | The public value. It starts with `nr_live_`, or with `nr_test_` for a test key. The SDK sends it on every request. |
| **HMAC secret** | A second secret that signs the request body. The SDK fetches it from `POST /api/v1/auth/verify` during authentication. |
| **Prefix** | The first 12 characters of the key. It identifies the key in list views and logs. |
| **Workflow** | The workflow the key is bound to. |

The control center shows the key value once, right after you create it. The
create API returns the signing secret too, in `secret_key`. The server
stores it and returns it again from `POST /api/v1/auth/verify`, so a
client holding the API key can always fetch the signing secret. Treat it
as sensitive.

### Using the key in the SDK

The SDK reads one environment variable:

```bash title="env"
export NULLRUN_API_KEY=nr_live_xxx...
```

```python
import nullrun

nullrun.init()  # reads NULLRUN_API_KEY from the environment

@nullrun.protect
def my_agent(prompt):
    return call_llm(prompt)
```

`NULLRUN_API_URL` overrides the gateway URL if you point the SDK at
your own deployment.

The API key identifies the caller. The HMAC secret proves the request
came from the holder of that secret: the SDK signs the request body
and the gateway verifies the signature on the gate, execute, track and
track/batch endpoints. `/api/v1/check` returns 410 Gone.

The SDK fetches the signing secret from `POST /api/v1/auth/verify`
during authentication and signs with the server's copy.
`NULLRUN_SECRET_KEY` is read at start-up and then replaced by that
value, so setting it yourself changes nothing.

`nullrun.init()` raises `NullRunAuthenticationError` when no key is
set. It creates the runtime and authenticates it against the gateway
immediately, so set the environment variables before you call it.

### Scopes

A scope says what a key may do. Every key is created with the same
four:

| Scope | What it allows |
|---|---|
| `gate` | Ask the gateway for a policy decision on a protected call |
| `execute` | Re-check a call after an approval was granted |
| `track` | Report the token counts and cost of a completed call |
| `verify` | Complete the authentication handshake on first use |

You cannot narrow them. The server rejects a request that carries a
non-empty `scopes` value with HTTP 400 — an empty array means the
default set — and provisions every new key with the full set.

### Rotating a key

Rotation issues a **new key value**. The new key keeps the old key's
name, workflow binding and HMAC secret, so it does the same job — only
the value changes.

The old key keeps working for 24 hours. Deploy the new value, confirm
the agent still runs, and let the grace window close. After 24 hours
the old key is refused with `401 API_KEY_REVOKED`.

```bash title="shell"
curl -X POST "https://api.nullrun.io/api/v1/orgs/$ORG_ID/api-keys/$KEY_ID/rotate" \
  -H "Authorization: Bearer $ORG_ADMIN_KEY"
```

The bearer must be a user-bound organization key with the Admin role.
An unbound machine key is refused. Admin authority needs the plan's
RBAC feature (Growth and above); on Lite and Starter only the Owner can
rotate or revoke a key.

The response carries the new key value. It is shown once.

### Revoking a key

Revoking stops the key. The next request with that key is refused with
`401 API_KEY_REVOKED`.

Revoke a key when:

- the key leaked
- the agent behind it is decommissioned
- the workflow it belongs to is going away

```bash title="shell"
curl -X DELETE "https://api.nullrun.io/api/v1/orgs/$ORG_ID/api-keys/$KEY_ID" \
  -H "Authorization: Bearer $ORG_ADMIN_KEY"
```

Revoking raises an alert titled **API key revoked**. It names the key
and who revoked it.

### Listing keys

The **API keys** page lists every key in your organization. You can
filter by workflow and by last-used status.

Each row shows:

- **Name** — with the key prefix and the scopes it grants
- **Status**
- **Created**
- **Last used** — when the key last made a request
- **Workflow**
- **Lifetime spend**

The full key value is never shown again. Only the prefix.

### Common questions

#### "How many keys do I need?"

One per workflow at minimum. For production, one key per environment
and one key per service. That way you can revoke staging without
touching production, and rotate one instance without restarting the
others.

#### "Can one key serve two workflows?"

No. A key is bound to one workflow when it is created. If the same
agent logic runs against two workflows, create two keys and pick
between them.

#### "What happens when a key expires?"

Requests with that key stop working. The error is `401
API_KEY_EXPIRED`. Rotate to get a new value, or create a new key.

#### "Can I see who used a key?"

The **Last used** column gives you the most recent activity. The audit
log records gate decisions for your organization on plans that include
it (Growth and above). A row does not name the key that made the call.

#### "Should I ever disable the gate?"

No. Without a protected call there is no decision, so nothing is
enforced and nothing is recorded.

### See also

- [Workflows](#41-workflow-context) — what the key is bound to
- [Configuration](#15-configuration) — the
  environment variables
- [Troubleshooting](#91-troubleshooting) — "why am I getting 401?"


# 3. Cost & safety


## 3.1 Budgets

A **budget** is the maximum amount of money a workflow may spend in one
billing period. Set it too low and your agent stops working. Set it
too high and a runaway agent burns real money.

Amounts are always in **cents**. `$50.00` is `5000`.

### Which cap binds

Two caps can apply to the same workflow:

| Cap | Where it comes from | Counter it is measured against |
|---|---|---|
| Org ceiling | A `BudgetLimit` policy with scope **Org** | One counter shared by every workflow in the organization |
| Workflow ceiling | A `BudgetLimit` policy with scope **Workflow** | One counter per workflow |

Both apply. The control center shows the smaller of the two as the
effective cap. The org ceiling is **always strict** — it is enforced
even when the workflow's own policy uses Soft mode.

A workflow with no `BudgetLimit` policy of its own has no workflow
ceiling. The org ceiling still applies to it.

### Where you see it

The **Budget** card on a workflow's **Overview** tab shows the spend
for the current period against the effective cap, a progress bar, and
a caption that names where the cap came from.

<figure class="nr-shot">
  <img class="nr-shot__light" src="../assets/images/screenshots/workflow-detail-light.png"
       alt="Workflow detail — Overview tab. The Budget card sits at the top showing spent / cap."
       loading="lazy" decoding="async">
  <img class="nr-shot__dark" src="../assets/images/screenshots/workflow-detail-dark.png"
       alt="Workflow detail — Overview tab. The Budget card sits at the top showing spent / cap."
       loading="lazy" decoding="async">
  <figcaption class="nr-shot__caption">Workflows · Budget card</figcaption>
</figure>

### What the budget covers

The budget covers **spend**, not calls. Calls are rate-limited
separately — see [Policies](#22-policies).

"Spend" is calculated from the token counts your LLM provider reports
and the per-model prices the gateway holds:

- **Input tokens** × input rate
- **Output tokens** × output rate
- **Cache read** and **cache write** tokens, at their own rates
- **Reasoning tokens**, at the reasoning rate

The total is the sum across every `@protect` call for the current
period.

### Periods

A **period** is the window after which the spend counter resets. The
period comes from the server, not from your agent.

| Plan | Period source | When it resets |
|---|---|---|
| **Lite** | A rolling month anchored at signup | One month after signup, then every month after that |
| **Paid** | Your billing cycle | On renewal |
| Any org with no billing cycle | The UTC calendar month | On the first of the month |

The control center shows the period start and end dates next to the spend
bar. When the period rolls over, the counter resets to zero and the
budget applies fresh.

### What happens at the boundary

Two scenarios, depending on the workflow's
[enforcement mode](#22-policies).

#### Hard mode

```
Spending → $49.95 of $50.00
Next @protect call:        #2.00 projected
gate decision:             block
SDK raises:                 NullRunBudgetError (NR-B004)
with nullrun.guard():     prints the developer report, sys.exit(1)
```

The agent stops at the boundary. The projected cost of the call is
reserved while the gate approves it, and the actual cost is booked
after the LLM returns. A refused call is never charged.

#### Soft mode

Soft mode lets the agent run past its workflow ceiling while an
active chain exists, up to a bounded overdraft. It needs the policy
to be scoped to a workflow, an active chain, and headroom under both
overdraft caps. If one is missing, the budget behaves as Hard.

The org ceiling still applies in Soft mode.

See
[Policies → Soft mode requirements](#22-policies).

### Reserve and consume

The gate reserves the projected cost of a call, then books the actual
cost once the call returns. Three rules hold:

- The counter is **period-bound**. The period comes from the server
  and is fixed for the call, so a reservation and the later booking
  always land in the same period.
- The amount is in **cents**. No floating point, no rounding drift.
- The booking may exceed the reservation by a **fixed-cent epsilon**
  only. The default is 1¢, and each policy can set its own
  `consume_epsilon_cents`. A percentage epsilon is not supported.

An actual cost above the reservation plus the epsilon is **rejected**:
the commit returns HTTP **422** with the wire code
`CONSUME_OVERBUDGET`, and the SDK raises
`NullRunConsumeOverbudgetError` (`NR-O001`). The call is never
silently re-reserved. The period counter still shows the real spend.

A transport retry does not double-charge. The SDK mints one
`operation_id` for a logical action and carries it across the
reserve, the approval check and the booking. A repeated booking with
the same id replays the original response instead of charging again.

### How to set the budget

The cap comes from a budget policy:

1. Open **Governance → Policies → New policy**.
2. Pick the type **Budget**.
3. Pick the scope — **Organization** for a ceiling on the whole
   organization, or one **Workflow** for a cap on that workflow alone.
4. Fill **Max cost (USD/month)**. `$50.00` is `5000` cents.
5. Save. The policy is active immediately.

The steps for every policy type are in
[Policies → How to create one](#22-policies).

A policy always carries a positive cap. The server rejects a
`budget_cents` of `0`. To remove a cap, deactivate or delete the
policy.

### When you change the budget mid-period

- **Raise** — the new cap applies to the next gate call.
- **Lower below the current spend** — no refund is issued. Calls are
  refused until the period rolls over, because the counter does not go
  down inside a period.

### Getting alerts

The spend alerts fire on the organization's monthly budget limit at
80%, 95% and 100%. The ladder and the channels are in
[Alerts → The budget ladder](#53-alerts).

### Approximate budget endpoint

To show "you have used X of Y" in your own report or a
notification, the gateway exposes an approximate-spend endpoint:

```bash title="shell"
curl -sS "https://api.nullrun.io/api/v1/budget/approximate" \
  -H "Authorization: Bearer ${NULLRUN_API_KEY}"
```

The response carries:

| Field | Meaning |
|---|---|
| `org_id` | The organization the key belongs to |
| `current_spend_cents_estimate` | Estimated spend for the current period, in cents |
| `is_approximate` | Always `true` |
| `source` | Where the number came from: `redis_period`, `postgres_outbox`, `last_known_redis` or `ui_local_cache` |
| `confidence` | `high`, `medium` or `low` |
| `last_updated_at` | ISO-8601 UTC timestamp of the read |

**Use this for display only.** Never for enforcement, rate-limit logic
or agent-side gating. When no source is available the endpoint returns
**503** with `error_code = "BUDGET_DATA_UNAVAILABLE"`. Render that as
"data unavailable", never as `≈ $0 spent` — a missing figure and an
empty one are different claims.

### See also

- [Workflows](#41-workflow-context) — where the budget lives
- [Policies](#22-policies) — rate limits and the soft-mode fields
- [Error handling](#43-error-handling) — the exception each refusal
  raises
- [Troubleshooting](#91-troubleshooting)


## 3.2 Human approval

Some operations need a human to click **Approve** before they run.
Sending an email to a customer, moving money, deleting a record —
operations where you want a paper trail and a conscious decision.

When the agent hits an approval rule, the call parks. The agent stays
parked until a human decides, or the approval expires.

This page covers the rule and the wire contract. The operator's review
surface — what a pending request shows, how to approve or deny it — is
in [Approvals](#51-approvals-ui-surface).

### Approval rules — separate from ToolBlock

Approval rules are not `ToolBlock` policies with an `action =
require_approval` field. They are a separate rule object:

| Field | Purpose |
|---|---|
| `workflow_id` | The workflow the rule applies to. Every rule is scoped to one workflow. |
| `tool_patterns` | Glob patterns matching the tool name |
| `per_call_threshold_cents` | Projected-cost threshold. A wire field; the control center sends `null`. |
| `action_predicate` | Typed predicate over the call's impact |
| `action_label` | Label shown in the control center. Up to 255 characters. |
| `priority` | Order among the rules that match. Lower wins. Range 0–1000. |
| `expires_in_seconds` | How long the operator has to decide. 30–3600 seconds. |
| `risk_level` | `LOW`, `MEDIUM` or `HIGH`. Defaults to `MEDIUM`. |

Rules live under **Governance → Approval rules**. That page needs the
approvals feature, which is on Growth and above.

When a protected call matches an approval rule, the gate returns
`decision = "require_approval"` and the SDK parks until the operator
decides.

### When a rule fires

Two fields can fire the same rule:

- **`per_call_threshold_cents`** — projected execution cost in cents,
  evaluated against the estimated tokens the SDK reports.
- **`action_predicate`** — a typed condition over a structured impact
  extracted from the live call.

When both are set, the rule fires only when **both** pass. Either may
be absent, in which case it does not contribute. A rule with neither
matches every call.

#### Typed predicates

Two predicate kinds are supported on `action_predicate`.

**`money_amount`** — a per-call monetary threshold:

```json
{
  "kind": "money_amount",
  "direction": "outflow",
  "operator": "gt",
  "threshold_minor": 5000,
  "currency": "USD"
}
```

`direction` is `outflow` or `inflow`. `operator` is `gt`, `gte` or
`eq`. `threshold_minor` is a non-negative integer count of cents, so
`5000` is `$50.00`. `currency` must be `USD`.

**`tool_parameters`** — a disjunction over up to 5 named parameters,
with `equals`, `one_of`, `numeric_range`, `regex` and `exists`
matchers:

```json
{
  "kind": "tool_parameters",
  "trigger_logic": {"logic": "any"},
  "conditions": [
    {"param_name": "refund_amount", "matcher": {"type": "numeric_range", "min": 500}},
    {"param_name": "recipient", "matcher": {"type": "regex", "pattern": "^(?!internal@).*"}}
  ]
}
```

`trigger_logic` takes `{"logic": "any"}`, `{"logic": "all"}` or
`{"logic": "groups", "groups": [[0, 1], [2]]}`. The groups form lists
AND-groups of condition indices joined by OR. The default is `any`.

The `tool_parameters` predicate reads the canonical argument bag on the
wire: `tool_arguments`, then `tool_params`. MCP tool calls carry it.
A plain `@protect` function does not, so the predicate cannot be
evaluated and the call escalates to a human instead of matching on the
argument. The `money_amount` predicate is unaffected — it reads
`business_impact`, which the SDK does ship.

### `action_digest` — the binding

The gate computes a SHA-256 digest of the action's impact payload
and stores it on the approval row.

After the operator clicks Approve, the SDK sends the live payload and
its digest back to the gateway on the post-approval call. The gateway
recomputes the digest from that payload and compares it with the one
the operator approved. The comparison is atomic, so two concurrent
re-checks cannot both spend the same grant.

**The digest binds the approval to the exact payload.** A changed
amount, a changed argument, or a changed tool name makes the digest
differ from the approved one, and the call is refused:

| Situation | Result |
|---|---|
| The payload matches the approved one | The grant is consumed and the call proceeds |
| The impact payload drifted | Refused, `error_code = "NR-A013"` |
| The tool digest drifted | Refused, `error_code = "NR-A014"` |
| The grant was already consumed | Refused, `error_code = "NR-A015"` |
| The executing tool is outside the approved tool set | Refused, `error_code = "NR-A017"` |

### Approval resume flow

1. The SDK sends the gate request with the live impact payload. The
   gate evaluates the approval rules and one matches.
2. The gate creates a pending approval row with the payload, its
   digest, and an expiry set server-side. It notifies the configured
   channels.
3. The gate returns `decision = "require_approval"` with the
   approval id and the timeout.
4. The SDK parks until the operator decides.
5. The operator clicks Approve or Deny in the control center.
6. The gateway publishes the resolution on the WebSocket channel.
7. The SDK wakes up and resumes with the operator's outcome.

A denial reaches the agent as `NullRunApprovalDeniedError` (`NR-A011`).

If no decision arrives within the timeout, the SDK **fails closed**
and raises `NullRunApprovalExpiredError` (`NR-A012`). There is no
HTTP polling fallback for approvals: a silent network must not
silently approve a privileged action.

An approval request reaches your channels only if the
`approval_required` event subscription is on. The **Approval required**
subscription is off in the notification settings by default. An
organization that has never saved its notification settings still
announces approval requests on its configured channels.
See [Notifications](#52-notifications).

### When to use approval instead of blocking

Approval fits when:

- The operation is sensitive but you want the agent to be able to do
  it under human review.
- The blast radius is bounded — one email against a whole database
  drop.
- Someone is on call and can review within minutes.

Blocking fits when:

- The operation is never legitimate, such as `db.drop` in a
  read-only workflow.
- The blast radius is unbounded.
- No one can review approvals in time.

Approval is a feature, not a default. Start by blocking, and move
specific patterns to approval as the need arises.

### What's logged

Every approval decision lands in **Governance → Audit log**. Filter by
actor (the approver), decision (`approved` or `denied`) and time
window. The row carries the action digest and the tool name.

The action digest is the anchor that proves the operator approved the
exact payload the agent sent — not "any refund", but that amount and
those arguments.

### See also

- [Approvals](#51-approvals-ui-surface) — the operator's review surface
- [Tool policies](#23-tool-policies) — `ToolBlock` rules
- [Sensitive tools](#24-sensitive-tools) — when blocking is enough
- [Workflows → How to control one](#41-workflow-context) —
  Pause and Kill work the same way
- [API keys](#25-api-keys) — how to mint a key bound to a workflow

<figure class="nr-shot">
  <img class="nr-shot__light" src="../assets/images/screenshots/approval-rules-light.png"
       alt="Approval rules page with the New rule button highlighted in the top right."
       loading="lazy" decoding="async">
  <img class="nr-shot__dark" src="../assets/images/screenshots/approval-rules-dark.png"
       alt="Approval rules page with the New rule button highlighted in the top right."
       loading="lazy" decoding="async">
  <figcaption class="nr-shot__caption">Governance · Approval rules · New rule</figcaption>
</figure>


# 4. Runtime


## 4.1 Workflow context

A **workflow** is one agent you run. It appears under **Workflows** in
the sidebar. Each workflow has its own policies, its own budget and its
own API keys.

### What you see in the control center

The **Workflows** page lists every workflow in your organization. Each
row shows:

- The workflow's name and its external id
- Its state — **Active**, **Paused** or **Archived**
- The gate decisions recorded for it in the current billing period
- Spend against its budget cap for the current period. No cap set means
  it draws on the organization budget.
- When it last reached the gate

A killed workflow sits on the **Archived** tab. The **Flagged** and
**Tripped** tabs list the workflows whose circuit breaker is not fully
closed.

Open a workflow for its detail page. The page has six tabs:

| Tab | What it shows |
|---|---|
| **Overview** | Name, state, spend against the cap, the last gate activity, and the **Pause**, **Resume**, **Kill** and **Delete** controls. |
| **Policies** | The effective controls, the approval rules attached to this workflow, and the stacked policy list. |
| **Executions** | Every gate call this workflow made — allowed, blocked, rate-limited |
| **Traces** | The nested view of one run: every LLM call, every tool call, with timing and cost |
| **API keys** | The keys bound to this workflow. **Generate key** mints a new one and shows the value once. You revoke a key here. |
| **Coverage** | The tools and MCP servers observed on this workflow, and what is not governed yet |

### How to create one

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
  <img class="nr-shot__light" src="../assets/images/screenshots/workflows-list-light.png"
       alt="Workflows list with the New workflow button highlighted in the top right."
       loading="lazy" decoding="async">
  <img class="nr-shot__dark" src="../assets/images/screenshots/workflows-list-dark.png"
       alt="Workflows list with the New workflow button highlighted in the top right."
       loading="lazy" decoding="async">
  <figcaption class="nr-shot__caption">Workflows · New workflow</figcaption>
</figure>

<figure class="nr-shot">
  <img class="nr-shot__light" src="../assets/images/screenshots/workflow-new-light.png"
       alt="Create workflow dialog open — Workflow name field and External ID optional field."
       loading="lazy" decoding="async">
  <img class="nr-shot__dark" src="../assets/images/screenshots/workflow-new-dark.png"
       alt="Create workflow dialog open — Workflow name field and External ID optional field."
       loading="lazy" decoding="async">
  <figcaption class="nr-shot__caption">Workflows · Create dialog</figcaption>
</figure>

### How to control one

A workflow has three states you control from the control center or the API:
**Active**, **Paused** and **Killed**.

| State | What the agent sees |
|---|---|
| Active | Calls run normally |
| Paused | Protected calls are refused with `WorkflowPausedException` (`NR-W003`) |
| Killed | Protected calls are refused with the kill signal (`NR-W002`) |

Pause and Kill reach a running agent over a WebSocket push, so the
agent does not have to wait for its next call to learn. See
[Control plane](#44-control-plane-websocket) for the full contract.

Killed is terminal. There is no way back to Active from Killed.

### What actually runs

A workflow can carry its own budget ceiling, and it has no approval
switch of its own. It holds **policies**, and the gate combines them
with the organization's policies and the plan tier into the controls
that actually run. The **Policies** tab shows the result, under
**Effective controls**.

Two sections:

| Section | Rows it holds |
|---|---|
| **Spend** | The budget cap, whether a ceiling is in force, the enforcement mode, and the organization ceiling |
| **Rate** | The per-key call limit, the per-organization ceiling, and the loop guard |

Each section splits its rows in two. The controls this workflow's own
policies drive, and the ceilings it inherits from the organization or
the plan tier. An inherited ceiling cannot be changed on this page.

The tab also shows the **Approval rules** attached to this workflow and
the **Stacked policies** list. Every approval rule attached to a
workflow is active — there is no switch to turn approvals on.

The budget cap comes from the workflow's own cap, from a `BudgetLimit`
policy, or from the organization ceiling. The **Budget** card on the
Overview tab shows the spend against the effective cap and names where
the cap came from. See [Budgets](#31-budgets).

Trace retention is not a workflow setting. It follows your plan's
window. See [Tracing](#42-tracing).

### Chain context

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

#### When a chain ends

A chain closes on the **first** of:

- `op="end"`
- five minutes without a protected call
- one hour of chain lifetime

For a long stream, send a heartbeat roughly every 30 seconds. See
[Heartbeat](#69-stream-responses).

#### Why chains exist

Chains exist so the gate can tell "one call that happens to be
expensive" from "a sequence of calls that together cost more than
the budget". With an active chain, a Soft-mode policy lets the agent
run past its budget up to the overdraft cap. See
[Policies → BudgetLimit extra fields](#22-policies).

### How the workflow ends

A workflow has no end state. It stays **Active** across many runs, and
each run is a sequence of protected calls. The workflow keeps its
policies, budget and key bindings. Run the agent again next week and
the same workflow handles it.

### See also

- [Budgets](#31-budgets) — the budget cap and how the period rolls over
- [Policies](#22-policies) — the rules attached to a workflow
- [Control plane](#44-control-plane-websocket) — how Pause and Kill reach the agent
- [API keys](#25-api-keys) — how to mint a key bound to this workflow


## 4.2 Tracing

A **trace** is one run of your agent. A **span** is one step inside
it. The control center puts traces under **Executions** and **Traces** in
the sidebar.

When a user reports "the agent did something odd at 14:30", the trace
is where you look.

### What you see in the control center

The **Executions** page lists the executions your organization ran.
Each row shows the execution id, the action, the agent, the workflow,
the model, the tool, the token count, the result, the cost and the
time. The four counters above the table count gate decisions —
**Allow**, **Block**, **Pending** and **Denied**. A blocked call has no
row, because it produced no execution. The **CSV** button downloads the
rows on the screen as a CSV file.

<figure class="nr-shot">
  <img class="nr-shot__light" src="../assets/images/screenshots/executions-light.png"
       alt="Executions page listing every agent run with workflow, duration, status and cost columns."
       loading="lazy" decoding="async">
  <img class="nr-shot__dark" src="../assets/images/screenshots/executions-dark.png"
       alt="Executions page listing every agent run with workflow, duration, status and cost columns."
       loading="lazy" decoding="async">
  <figcaption class="nr-shot__caption">Executions</figcaption>
</figure>

The **Traces** page lists the runs. Above the table, four tiles count
the loaded runs, the ones that succeeded, the ones that errored, and
the median duration.

<figure class="nr-shot">
  <img class="nr-shot__light" src="../assets/images/screenshots/traces-light.png"
       alt="Traces page with the waterfall of LLM and tool calls for a single execution."
       loading="lazy" decoding="async">
  <img class="nr-shot__dark" src="../assets/images/screenshots/traces-dark.png"
       alt="Traces page with the waterfall of LLM and tool calls for a single execution."
       loading="lazy" decoding="async">
  <figcaption class="nr-shot__caption">Traces · Waterfall</figcaption>
</figure>

Open one and you get a header with the start time, the end time, the
total duration and the number of spans, with the error count
alongside it. Under the header is the waterfall.

The waterfall is the trace. Each row is one span:

- The **name** of the protected function
- A **duration bar**, positioned against the longest span in the trace
- A **status** — ok or error
- The **policy verdict** for that call, when the gate recorded one
- The **span id**, in the row tooltip. The audit log carries no span
  column, so you reach an audit row through the execution id.

Nested calls sit under their parent, so a supervisor that calls
sub-agents renders as one tree rather than several. Click a row to
pin its details.

### How spans are created

The SDK emits a span for every protected call. You do not add
instrumentation yourself.

```python
import nullrun

@nullrun.protect
def research(question):
    return call_llm(question)
```

A call to `research` opens a span and closes it when the call returns.
A protected call inside another protected call becomes a child span.

The context managers set the parent, so you control the shape of the
tree:

| Context manager | What it does |
|---|---|
| `with nullrun.workflow("name"):` | Sets the workflow for every call inside the block |
| `with nullrun.span("phase"):` | Names the phase; calls inside become its children |
| `with nullrun.agent("name"):` | Attributes the calls to one agent |

```python
import nullrun

with nullrun.workflow("support-bot"):
    with nullrun.span("research"):
        research(question)
```

LLM calls are reported separately from spans. The SDK sends the token
counts your provider reports, and the gateway prices them. The call
is attached to the span that was active when it happened.

### Identifiers

| Field | What it identifies |
|---|---|
| `trace_id` | One run. The same on every span in that run. |
| `span_id` | One protected call |
| `parent_span_id` | The span this one sits under |

Open a run by its `trace_id` in the trace URL. The audit log filters by
execution id, not by trace id.

### What is not stored

NullRun never persists prompt content or LLM response bodies. A span
carries the function name, the timing, the status and the verdict —
not the text you sent or the text you got back. See
[Error handling → What is NOT stored](#43-error-handling).

### How long traces are kept

Traces follow your plan's retention window:

| Plan | Retention |
|---|---|
| Lite | 3 days |
| Starter | 7 days |
| Growth | 30 days |
| Scale | 90 days |
| Enterprise | Unlimited |

When a trace expires, the aggregated spend survives, summarised per
workflow per period.

Retention is separate from the volume caps. Lite also throttles to
**10 000 tokens per hour** and **75 000 executions per month**, so a
Lite workflow stops producing traces inside the 3-day window. See
[Billing & Plan → Caps](#55-billing-plan).

Export the rows you need; the retention window removes them. The
**CSV** button on the Executions page writes the rows on the screen as
a CSV file, not the organization's whole history.

### Common questions

#### "My trace shows nothing"

The runtime was never created, so no span was ever emitted. Check that
`NULLRUN_API_KEY` is set and that the first protected call actually
ran.

#### "My trace is incomplete"

The SDK buffers events and flushes them on a timer. A process that
dies with the buffer unflushed loses the spans still in flight.
`init()` registers a clean shutdown at exit, so a normal exit reaches
the gateway.

#### "One LLM call is counted twice"

The SDK's auto-instrumentation already reports the token counts for
the LLM clients it supports. If you also report the same call with
`get_runtime().track_llm(...)`, the call is booked twice. Pick one.

#### "Why is my trace missing a step?"

The control center shows one span per protected call. A helper function
that is not decorated with `@protect` produces no span. Decorate every
call you want to see in the tree.

### See also

- [Workflows](#41-workflow-context) — the `workflow()` context manager
- [Error handling](#43-error-handling) — how errors map to spans
- [Budgets](#31-budgets) — where the cost in a trace comes from


## 4.3 Error handling

Errors in NullRun come in three layers, one for each audience: your
code, your monitoring, and your end user. The SDK ships all three.
You pick how much of each to use.

| Layer | Mechanism | Audience |
|---|---|---|
| 1. Structured exception | `except NullRunError` | Your code — retry, fail, or surface it |
| 2. `on_error` hook | `@nullrun.on_error` | Sentry, Datadog, your log aggregator |
| 3. `guard()` / `format_user_message` | `with nullrun.guard():` | The end user — one clean sentence |

### Layer 1 — the structured exception

Every NullRun exception carries four fields:

| Field | What it is | Example |
|---|---|---|
| `error_code` | Stable machine-readable identifier | `NR-B004` |
| `user_action` | What to do next | `Request a fresh approval row and retry /gate.` |
| `retryable` | Whether a backoff retry makes sense | `True` for a rate limit, `False` for a budget |
| `docs_url` | Link to the code's reference page | `https://docs.nullrun.io/errors` |

#### The hierarchy

Every public exception inherits from `NullRunError`. Two marker classes
split it by kind of event:

| Marker | What it covers |
|---|---|
| `NullRunDecision` | The gate reached a verdict — budget cap, tool block, approval, chain rejection, workflow pause |
| `NullRunInfrastructureError` | The SDK could not reach or read the gateway — network, 5xx, auth, config |

One class sits outside both: `WorkflowKilledInterrupt`, the
control-plane kill signal. It inherits from `NullRunError` directly, so
`except NullRunDecision` does not catch it. Catch it by name.

The full tree, with every class and its code, is in
[Reference → Errors](#75-error-codes).

#### Retry or not

`retryable` tells you whether a backoff retry is the right response.

| Retryable | Codes |
|---|---|
| `True` | `NR-B001`, `NR-B002`, `NR-R001`, `NR-R002`, `NR-P002`, `NR-P004`, `NR-A010`, `NR-B006`, `NR-A016`, `NR-MCP03` |
| `False` | Every other code |

The full catalog is in
[Reference → Errors](#75-error-codes).

#### Catching

Branch on the exception type when the outcome differs. Otherwise catch
the parent and read `error_code`:

```python
import nullrun
from nullrun import NullRunError, NullRunBudgetError

@nullrun.protect
def my_agent(prompt):
    try:
        return call_llm(prompt)
    except NullRunBudgetError:
        return "I have reached my budget for this period."
    except NullRunError as exc:
        # exc.error_code, exc.retryable, exc.user_action, exc.docs_url
        raise
```

For a rate limit, the exception carries the wait the server asked for:

```python
from nullrun import RateLimitError

try:
    my_agent(prompt)
except RateLimitError as exc:
    # exc.retry_after is the number of seconds the server asked for.
    # exc.upgrade_url points at the plan upgrade page when the limit
    # is a plan limit.
    time.sleep(exc.retry_after)
```

### Layer 2 — the `on_error` hook

Register a hook and it fires for every `NullRunError` that
propagates:

```python
import nullrun
import sentry_sdk

@nullrun.on_error
def _to_sentry(err, ctx):
    sentry_sdk.capture_exception(err, extra={
        "code": err.error_code,
        "retryable": err.retryable,
        "stage": ctx.stage,
        "workflow_id": ctx.workflow_id,
        "tool_name": ctx.tool_name,
    })
```

The hook fires once per error, in registration order. A hook that
raises is caught and logged — a broken Sentry integration cannot break
your agent.

The context object carries:

| Field | Meaning |
|---|---|
| `stage` | Where the error fired: `init`, `auth`, `policy_fetch`, `execute`, `track`, `gate`, `check`, `sensitive_tool`, `org_status`, `ws`, `transport` |
| `workflow_id` | The active workflow, or `None` if the error fired with no workflow bound |
| `tool_name` | The tool that triggered the error, or `None` |
| `api_key_prefix` | A short non-secret fingerprint of the key in use |
| `correlation_id` | Per-request identifier |
| `timestamp` | When the error fired |
| `extra` | Free-form dict for stage-specific metadata |

**The kill signal fires the hook on the sync path only.** See
[Kill signal](#kill-signal).

Registering several hooks is fine. Each returns a callable that
unregisters it.

### Layer 3 — `guard()` and `format_user_message`

For a script that should print a friendly message and stop, wrap the
call:

```python
import nullrun

@nullrun.protect
def my_agent(prompt):
    return call_llm(prompt)


if __name__ == "__main__":
    with nullrun.guard():
        print(my_agent("What does NullRun do?"))
```

`guard()` catches every `NullRunError` raised inside the block,
prints a developer report to stderr, and exits with code 1. The report
has the catalog headline plus the code, the stage, the endpoint, the
cause, the fix, and a link:

```
Too many requests. Please wait a moment and try again.
  [NR-R001] what: /api/v1/gate (retryable)
           where: endpoint=/api/v1/gate status=429 source=GATEWAY_ERROR
           why: Transport error on /api/v1/gate: rate limit exceeded (source=GATEWAY_ERROR, details={'retry_after': 30.0})
           how to fix: The NullRun backend rate-limited this API key. Wait retry_after seconds (or upgrade the plan) before retrying.
           docs: https://docs.nullrun.io/errors
```

`guard()` accepts `exit_code` if you want a different status.

A non-NullRun exception propagates unchanged — your own bugs deserve an
honest traceback. The kill signal is the one NullRun exception with a
special rule, described in [Kill signal](#kill-signal).

#### Branded wording

Override the user-facing sentence for one code at the top of your
entry point:

```python
import nullrun

nullrun.set_user_message(
    "NR-B004",
    "You've used all your support credits. Upgrade to keep chatting.",
)
```

Overrides live in a per-process dict. They do not persist across
processes and they are not synced to the gateway.

### Server frameworks

`guard()` exits the process, so it does not fit a request handler.
Catch the exception and map it to an HTTP status yourself:

```python
import nullrun
from nullrun import NullRunError

@app.post("/chat")
async def chat(req: ChatRequest):
    try:
        return await run_agent(req.message)
    except NullRunError as exc:
        raise HTTPException(
            status_code=getattr(exc, "status_code", None) or 503,
            detail={
                "message": nullrun.format_user_message(exc),
                "code": exc.error_code,
            },
        )
```

Only some exception classes carry `status_code`, so read it with
`getattr`. `format_user_message(exc)` always returns a non-empty string
that is safe to show an end user.

### Kill signal

The operator can kill a running workflow. The signal arrives as
`WorkflowKilledInterrupt`, or its typed alias
`NullRunWorkflowKilledError`. How it reaches your code depends on the
`@protect` flavour:

| Flavour | What reaches your code |
|---|---|
| async `@protect` | The raw `WorkflowKilledInterrupt` propagates. The `on_error` hook stays silent. |
| sync `@protect` | It arrives re-wrapped as `NullRunBlockedException` with `error_code = "NR-W002"`. The hook fires. |

So `except WorkflowKilledInterrupt:` catches the kill on the async path
only. On the sync path, catch `NullRunBlockedException` and read
`error_code`.

`guard()` follows the same split. On the async path it re-raises the
kill, so the kill reaches the top of the agent loop. On the sync path
the kill is already a `NullRunBlockedException`, so `guard()` prints
the report and exits with status 1.

To keep the process alive after a kill — checkpoint, notify a
supervisor, then exit — use a bare `@protect` with your own
`except NullRunBlockedException:` arm and check `error_code == "NR-W002"`.

### Fail closed

Every check on the enforcement path **refuses** when it cannot be
evaluated. A refusal is a refusal, not a pass. The body of a
protected function does not run on a refused call.

| Situation | Result |
|---|---|
| The gateway cannot be reached | The body does not run. A network failure raises `NullRunBlockedException` with `NR-B001`, a gateway 5xx raises `NullRunBlockedException` with `NR-B002`, and a rejected key raises `NullRunAuthError` with `NR-A003` |
| The rate-limit store cannot be reached | HTTP 503 `RATE_LIMIT_REDIS_UNAVAILABLE` |
| The budget store cannot be reached | HTTP 402 `BUDGET_REDIS_UNAVAILABLE` |
| A `ToolBlock` policy cannot be evaluated | HTTP 403 `TOOL_BLOCKED` |
| The approval window closes with no decision | `NullRunApprovalExpiredError` (`NR-A012`) |

The SDK circuit breaker is the one local exception. After repeated
transport failures it stops the event flush and keeps the pending events
on disk. It never lets a protected call through unchecked. See
[Circuit breaker](#21-circuit-breaker).

### Audit trail

Gate decisions land in **Governance → Audit log**. Each row carries the
decision, the reason code, the matched rule, the policy, the execution
id and the tool name. It answers "why did my agent stop working at
14:32?".

The log is hash-chained: each row carries the hash of the row before
it. `GET /api/v1/orgs/{org_id}/audit-log/verify` recomputes the chain
and names the first row that does not match.

The **Audit log** page needs the plan's audit log feature. Lite and
Starter do not include it, so those plans record no gate decisions.
Pair it with [Traces](#42-tracing) for the request behind the decision.

### What is NOT stored

NullRun never persists:

- **Prompt content** or **LLM response payloads**. The gate receives
  only the model name, the tool name, the tool list, an estimated
  token count and an optional typed `business_impact` payload.
- **Card numbers, CVC, expiry month or year.** Subscriptions carry
  only the payment method brand and its last four digits.
- **OAuth refresh tokens.** The identity provider owns session
  lifetime.

Tool arguments are the one case worth naming. The SDK ships the
argument bag so the gate can evaluate a `tool_parameters` approval
predicate and bind the approval digest to those exact arguments. The
control center renders the tool name and the argument count, not the
values.

Personal data is redacted at the log boundary: email addresses, phone
numbers, card numbers and tokens are replaced with a marker before the
row is written. Uppercase `KEY=VALUE` pairs are rewritten to
`KEY=[REDACTED]` before the bytes reach stdout.

### See also

- [Reference → Errors](#75-error-codes) — the full catalog
- [Troubleshooting](#91-troubleshooting) — common failures and fixes
- [Use with FastAPI](#64-use-with-fastapi) — exception handling in
  ASGI handlers
- [Tracing](#42-tracing) — how errors map to spans


## 4.4 Control plane (WebSocket)

The **control plane** is the live channel between the control center and a
running agent. An operator clicks **Pause**, **Resume**, or **Kill**,
and the agent reacts while it runs.

### What the operator can do

| Action | What the agent does |
|---|---|
| **Pause** | Protected calls are refused with `WorkflowPausedException` (`NR-W003`). The agent can catch it, save state, and wait. |
| **Resume** | Protected calls run normally again. |
| **Kill** | Protected calls are refused with the kill signal (`NR-W002`). See [Sync and async behave differently](#sync-and-async-behave-differently). |

Kill is terminal. A killed workflow does not run again.

Pause is recoverable. The agent can catch the exception, checkpoint,
and try again.

### How the signal reaches the SDK

The SDK opens a WebSocket to
`wss://api.nullrun.io/ws/control/{organization_id}` on its first
protected call. The upgrade request carries the same API key the SDK
uses for every other request, in the `X-API-Key` and `Authorization`
headers. It carries no body, so it carries no request signature. Every
frame the server sends is signed, and the SDK verifies the signature
before it reads anything out of the frame.

The SDK keeps a copy of the control-plane state for each workflow it
tracks:

- With the WebSocket connected, the server pushes every state change.
- Without a pushed state, the SDK reads the workflow state over HTTP
  from `GET /api/v1/status/{workflow_id}`.

Set `NULLRUN_TRANSPORT=http` to run the HTTP poll instead of the
WebSocket. The poll runs once per second and suits environments where
the WebSocket endpoint is blocked.

The SDK chooses the transport for you. You do not pass a flag to
enable the control plane.

### What the agent sees

Two exceptions cover the whole control plane:

| Exception | Code | Meaning |
|---|---|---|
| `WorkflowPausedException` | `NR-W003` | The operator paused the workflow. |
| `WorkflowKilledInterrupt` | `NR-W002` | The operator killed the workflow. `NullRunWorkflowKilledError` is a typed subclass with the same code. |

`WorkflowPausedException` carries `resume_after`: the number of
seconds the pause lasts. It is `None` when the pause carries no
duration.

#### Sync and async behave differently

The decorator translates the signal differently in a synchronous
function and in a coroutine.

| Protected function | What propagates |
|---|---|
| Sync | The signal is re-wrapped as `NullRunBlockedException` with `error_code` `NR-W002` or `NR-W003`. The `on_error` hook fires. |
| Async | The raw `WorkflowKilledInterrupt` or `WorkflowPausedException` propagates. The `on_error` hook does not fire. |

An async framework cancels a task on the original exception type, so
the async wrapper leaves it alone.

```python
import nullrun
from nullrun import WorkflowKilledInterrupt, WorkflowPausedException

nullrun.init(api_key="nr_live_...")


@nullrun.protect
def my_agent_step(prompt):
    # ... agent logic ...
    return result


try:
    my_agent_step("do something")
except WorkflowKilledInterrupt:
    # The operator killed the workflow. Checkpoint, then re-raise.
    raise
except WorkflowPausedException:
    # The operator paused the workflow. Save state and wait.
    raise
```

`nullrun.guard()` handles the pause: it prints the developer report
and exits with status 1. The kill follows the same split as the
decorator. On the async path `guard()` re-raises it, so the kill
reaches the top of the agent loop. On the sync path the kill is
already a `NullRunBlockedException`, so `guard()` prints the report
and exits with status 1.

### Approval events

The same WebSocket carries approval decisions. When the gate returns
`require_approval`, the parked agent waits for the operator. The
decision arrives over the control plane and the agent resumes with the
outcome.

If the approval window expires, the SDK raises
`NullRunApprovalExpiredError` (`NR-A012`). An approval never resolves
silently.

The full approval flow is in
[Human approval](#32-human-approval).

### Operator steps

#### Pause a runaway agent

1. Open **Workflows** in the sidebar.
2. Open the workflow row.
3. Click **Pause**.
4. The workflow status changes, and the agent stops at its next protected call.

#### Resume a paused agent

1. Open the workflow.
2. Click **Resume**.
3. The next protected call succeeds.

#### Kill an agent

1. Open the workflow.
2. Click **Kill**.
3. The agent receives the kill signal at its next protected call.

Catch the kill explicitly and re-raise it. A bare `except Exception:`
arm swallows the signal.

### See also

- [Workflows](#41-workflow-context) — where a workflow runs
- [Human approval](#32-human-approval) — the approval round trip
- [Error handling](#43-error-handling) — the exception each refusal raises


## 4.5 MCP servers (Action sources)

An **MCP server** is a source of tools for your agent. The agent
discovers the server's tools, and each call is evaluated by the gate
like any other tool call.

### How a tool is named

The canonical name of an MCP tool carries the server it came from:

```
mcp://{server}/{tool}
```

| Example | Server | Tool |
|---|---|---|
| `mcp://github/create_issue` | `github` | `create_issue` |
| `mcp://filesystem/read_file` | `filesystem` | `read_file` |

The server name is the first segment. The rest is the tool name, and it
may contain slashes.

The SDK does not build that name. `MCPAdapter.call_tool("create_issue", …)`
sends the bare tool name, and the gateway resolves the server from your
organization's own catalog. Exactly one catalog server declares that
tool, so the server on that row becomes the identity. A tool no server
declares stays a plain tool name.

Policy patterns are written against the canonical name. See
[Tool policies → What a tool name looks like](#23-tool-policies).

### Deciding which tools run

The **MCP servers** page in the control center lists the servers your agents
call and the tools they expose. Each tool carries one decision:

| Decision | What it means |
|---|---|
| **Allow** | The tool runs. |
| **Ask** | The tool is refused. The control center labels it "Behaves as block today". |
| **Block** | The tool is refused. |

A tool with no decision is refused. The operator has to choose.

The gate also compares the tool's current definition with the definition
the operator accepted. A changed definition is refused even when the
decision is **Allow**, and a tool the server has dropped is refused too.
The drift check runs before the decision, so a tool the operator allowed
and never re-accepted is refused first. Accepting the new definition does
not allow the tool — the operator still has to set the decision to
**Allow**.

### Refusals

The gate refuses an MCP call with one of these codes:

| Wire code | HTTP | SDK class | Meaning |
|---|---|---|---|
| `MCP_TOOL_BLOCKED` | 403 | `NullRunToolBlockedError` | The decision is block. |
| `MCP_TOOL_REMOVED` | 403 | `NullRunToolBlockedError` | The server no longer offers the tool. |
| `MCP_DEFINITION_DRIFTED` | 403 | `NullRunApprovalToolDigestMismatchError` | The tool's definition changed after the operator accepted it. |
| `MCP_TOOL_DECISION_REQUIRED` | 403 | `NullRunMcpApprovalRequiredError` | Nobody has chosen a decision for this tool. |
| `MCP_TOOL_APPROVAL_REQUIRED` | 403 | `NullRunMcpApprovalRequiredError` | The decision is ask. |
| `MCP_REGISTRY_UNAVAILABLE` | 503 | `NullRunBackendError` | The registry could not be read. The call is refused and can be retried. |

Two facts about `MCP_TOOL_APPROVAL_REQUIRED` catch people out:

- The wire decision is **block**, not `require_approval`. There is no
  approval row and no approval id. The refusal never reaches a human.
- The call succeeds once the operator changes the decision on the catalog
  row to **Allow**. There is no per-call approval round trip for an MCP
  tool.

Three MCP-specific codes exist in the SDK:

| SDK code | SDK class | Meaning |
|---|---|---|
| `NR-MCP01` | `NullRunMcpDestructiveBlockedError` | A destructive tool was blocked. |
| `NR-MCP02` | `NullRunMcpReadonlyBypassBlockedError` | A read-only bypass was blocked. |
| `NR-MCP03` | `NullRunMcpApprovalRequiredError` | The call needs an operator decision. |

`NR-MCP01` and `NR-MCP02` belong to the MCP umbrella policies. The gate
evaluates the per-tool decision instead, and the gate does not read the
umbrella policies. The two codes stay reserved so an SDK can tell the
refusal families apart.

`NR-MCP03` is what the SDK raises when the gate refuses with
`MCP_TOOL_APPROVAL_REQUIRED` or `MCP_TOOL_DECISION_REQUIRED`. It carries
`retryable = True`, because the operator can still decide.

### Calling an MCP tool from the SDK

`MCPAdapter` is the helper that gates MCP calls. It wraps a connected
MCP client, discovers the server's tools, and routes every call through
the gate before the client runs.

```python
import nullrun
from nullrun.toolbox.mcp import MCPAdapter

nullrun.init(api_key="nr_live_...")

# Your own MCP client — the adapter does not open the connection.
client = your_mcp_client_library.connect(url="https://your-mcp-server")

adapter = MCPAdapter(server_name="github", mcp_client=client)

result = adapter.call_tool(
    "create_issue",
    {"repo": "acme/api", "title": "Crash on checkout"},
)
```

What the adapter does on every call:

- Routes the call through the gate first. A refused call raises
  `NullRunBlockedException` and the MCP client is not invoked.
- Reads the server's tool list and forwards the tool's annotations to the
  gate. The `readOnlyHint`, `destructiveHint`, and `openWorldHint` hints
  become the gate's read-only, destructive, and open-world flags.
- Derives the action digest from the tool name and the exact argument bag
  it forwards, so an operator approval binds to that payload.

Two constructor options matter:

| Option | Effect |
|---|---|
| `cache_seconds` | How long the tool list is cached. Must be `0` or at least `30`. `0` re-reads the tool list on every call. |
| `runtime` | The runtime to gate through. Pass one to use a specific runtime; leave it unset to use the global one. |

When the tool list cannot be read, the adapter tells the gate that the
annotations are unknown. It never presents a stale hint as the server's
current answer.

### Getting an MCP tool approved

The registry decision and an approval rule are two different mechanisms.

The registry's **Ask** decision refuses the call and creates no approval
row. The operator changes the decision on the catalog row to **Allow**,
and the next call runs.

An [approval rule](#32-human-approval) is the mechanism that parks a call
for a human. When a rule matches, the gate returns `require_approval`,
and the adapter re-enters with the grant:

```python
from nullrun import NullRunError

try:
    result = adapter.call_tool(
        "create_issue",
        {"repo": "acme/api"},
        approval_id=approval_id,
    )
except NullRunError as exc:
    # exc.error_code tells you which refusal you got.
    raise
```

The adapter derives the digest and the impact envelope from the tool name
and the argument bag, so the grant binds to those exact arguments. The
wire contract for the approval is in
[Human approval](#32-human-approval).

### See also

- [Tool policies](#23-tool-policies) — the tool-name format and matching rules
- [Human approval](#32-human-approval) — writing an approval rule for one tool
- [Sensitive tools](#24-sensitive-tools) — starter patterns for destructive tools


# 5. Organization


## 5.1 Approvals (UI surface)

An **approval** is a tool call that an agent wants to make and a human has to authorise. The call parks until an operator decides, and the operator sees it on the **Approvals** page.

The approvals feature is on Growth and above. On a lower plan the sidebar entry carries a lock, and the page shows an upgrade prompt.

This page covers the review surface: what a request shows, how to decide, and what the agent sees afterwards. The rule format, the typed predicates, the digest binding, and the wire contract live in [Human approval](#32-human-approval).

### What a pending request shows

Each pending row carries:

| Field | What it tells you |
|---|---|
| **Tool and arguments** | The exact tool the agent wants to call and the arguments it wants to pass. |
| **Why it needs approval** | The rule that matched, in plain language. |
| **Risk** | `LOW`, `MEDIUM`, or `HIGH`. |
| **Time left** | How long the operator has to decide. |
| **Workflow** | The workflow that raised the request. |

The pending feed refreshes every 30 seconds, and the badge next to **Approvals** in the sidebar carries the pending count.

Click a row to open the full detail: the request id, the action fingerprint, the execution id, the rule, the tool patterns, the per-call threshold, the rule priority, the review window, the rule creation time, and the rendered predicate.

### Approving

The **Approve** button opens a **Confirm approval** dialog. The agent stays blocked until the operator confirms in the dialog.

| Risk | What the operator does |
|---|---|
| **LOW** | Click **Approve**, then **Confirm**. |
| **MEDIUM** | Click **Approve**, type the amount, then **Confirm**. |
| **HIGH** | Click **Approve**, type the amount, then **Continue**, type the action label, then **Confirm**. |

A request with no money amount has no amount to type. MEDIUM and HIGH requests then confirm on the action label alone. The action label is the tool name, or the action when the request carries no tool.

On approve, the grant is released and the agent resumes.

### Denying

Deny takes the same path at every risk level. The operator types a reason for the denial, then confirms with **Confirm Deny**.

The agent raises `NullRunApprovalDeniedError` (`NR-A011`) and the call does not run.

### Expiry

Every approval carries a review window, set by the rule that fired. When the window closes with no decision, the request expires and the agent raises `NullRunApprovalExpiredError` (`NR-A012`).

An approval never resolves silently. The operator has to click.

### How the grant binds to the payload

A grant is for one exact action, not for a tool name.

The gate stores a SHA-256 digest of the action's impact payload on the approval row. On the call that follows an approval, the gate recomputes the digest from the live payload and compares it with the approved one. The comparison is atomic, so two concurrent re-checks cannot both spend the same grant.

A changed amount, a changed argument, or a changed tool name breaks the digest, and the call is refused. The refusal codes and the wire contract are in [Human approval](#32-human-approval).

### History

The **History** tab holds the whole approval record. It has two sections:

| Section | Rows |
|---|---|
| Awaiting decision | Requests with no decision yet. |
| Decided | Requests that were approved, denied, expired, or consumed. |

The search box filters the rows by workflow, action, tool, reason, actor, or comment. The filter is part of the URL, so a filtered history can be shared as a link.

### Deciding in bulk

The toolbar above the pending queue counts the low-risk pending requests that are eligible for a bulk action. **Approve all N** opens a confirmation that lists each request. Nothing is sent until the operator confirms.

Medium- and high-risk requests are not eligible for a bulk approval. Each one takes its own type-to-confirm step.

### Programmatic approval

A CI bot or an on-call rotation decides through the REST endpoints — see [HTTP API → approvals](#73-http-api). An already-decided request answers `409 APPROVAL_ALREADY_DECIDED`; the codes are in [Error codes](#75-error-codes).

### Audit trail

Every approve and deny lands in the audit log with the operator, the decision, the timestamp, and the execution id. The audit log is a plan feature: on Lite and Starter no row is written.

### See also

- [Human approval](#32-human-approval) — approval rules, typed predicates, and the wire contract
- [Tool policies](#23-tool-policies) — blocking a tool outright
- [Notifications](#52-notifications) — where an approval request is announced
- [HTTP API → approvals](#73-http-api) — the REST endpoints


## 5.2 Notifications

The **Notifications** page configures every outbound signal NullRun sends. It lives under **Account** in the sidebar.

Notifications are on Starter and above. On Lite the sidebar entry carries a lock, and the page shows an upgrade prompt.

The page has two sections:

1. **Alert channels** — where signals land.
2. **Event subscriptions** — which events reach the channels.

Threshold rules are a third piece of the model, and the control center has no editor for them. Rules are configured over the REST API. See [Alerts](#53-alerts).

### Alert channels

Two channel types exist.

| Type | What it is |
|---|---|
| **Slack** | A Slack App channel. It is bound to a Slack installation and a Slack channel, and posts through Slack's API with a bot token. |
| **Webhook** | A generic HTTPS endpoint that receives a JSON POST. |

The two types do not post the same payload. The Slack App connection is
set up separately, and the **Add channel** dialog does not offer it. A
Slack incoming webhook URL is saved as a **Webhook** channel.

The API accepts `slack` and `webhook` only. A third type is refused.

#### Adding a channel

Click **Add channel** in the **Alert channels** section header and pick the type. The dialog asks for:

| Field | Meaning |
|---|---|
| **Name** | The label on the channel card and in alert messages. |
| **Webhook URL** | The HTTPS endpoint that receives the payload. |
| **Signing secret** | Optional. The key the receiver verifies the payload with. |
| **Test mode** | Suppress real alerts to this channel. |

With a signing secret set, every delivery carries four headers:

| Header | Meaning |
|---|---|
| `X-NullRun-Signature` | HMAC-SHA256 over `timestamp.nonce.body`. |
| `X-NullRun-Timestamp` | When the payload was signed. |
| `X-NullRun-Nonce` | A one-shot value that makes the delivery unique. |
| `X-NullRun-Event-Id` | The identifier of the event. |

A receiver should reject a timestamp that differs from its own clock by more than five minutes, and should remember a nonce for ten minutes. Compare the signature in constant time.

#### Test mode

A channel in test mode receives synthetic payloads only. Real alerts do not reach it. The channel card carries a **Test mode** badge.

#### Test send

**Test send** in the channel menu posts a synthetic payload and reports the outcome. The card shows **Test sent** or **Test failed**. Use it after creating or editing a channel, to confirm the endpoint delivers.

The card also shows the last delivery time, or **Never triggered**.

### Event subscriptions

The matrix decides which events reach which channels. Each row is an event. Each column is a channel. A filled dot means the channel receives that event.

The events are:

| Group | Event | Fires when |
|---|---|---|
| Workflow activity | `execution_quota_warning` | The organization approaches its execution limit. |
| Workflow activity | `workflow_budget_warning` | A workflow exceeds its budget. |
| Workflow activity | `loop_detected` | A workflow makes repeated identical calls. |
| Workflow activity | `policy_violation` | An action is blocked by policy. |
| Workflow activity | `workflow_killed` | A workflow is terminated. |
| Governance & access | `approval_required` | A new approval is requested. Off by default. |
| Governance & access | `api_key_created` | An API key is created. |
| Team | `member_invite` | A new member is invited. |
| Digest | `daily_summary` | The previous day's activity digest. |
| Digest | `weekly_summary` | The previous week's activity digest. |

The toggle on the right of a row switches the event on or off for every channel. The dots are read-only indicators of where the event lands, and a disabled channel shows a dashed cell.

### API

The same actions are available over REST.

| Method | Path |
|---|---|
| `GET` | `/api/v1/orgs/{org_id}/alert-channels` |
| `POST` | `/api/v1/orgs/{org_id}/alert-channels` |
| `PATCH` | `/api/v1/orgs/{org_id}/alert-channels/{channel_id}` |
| `DELETE` | `/api/v1/orgs/{org_id}/alert-channels/{channel_id}` |
| `POST` | `/api/v1/orgs/{org_id}/alert-channels/{channel_id}/test` |
| `GET` | `/api/v1/orgs/{org_id}/alert-rules` |
| `POST` | `/api/v1/orgs/{org_id}/alert-rules` |
| `PATCH` | `/api/v1/orgs/{org_id}/alert-rules/{rule_id}` |
| `DELETE` | `/api/v1/orgs/{org_id}/alert-rules/{rule_id}` |
| `GET` | `/api/v1/orgs/{org_id}/notification-settings` |
| `PATCH` | `/api/v1/orgs/{org_id}/notification-settings` |

The plan gate is enforced on the server. A Lite organization cannot create a channel by calling the API directly.

### See also

- [Alerts](#53-alerts) — what fired and what to do about it
- [Approvals](#51-approvals-ui-surface) — where an approval request is announced
- [HTTP API](#73-http-api) — the full endpoint catalog


## 5.3 Alerts

The **Alerts** page shows the signals an operator has to look at: a threshold the spend crossed, an action the gate stopped, an event about the organization.

Alerts are on Starter and above. On Lite the sidebar entry carries a lock, and the page shows an upgrade prompt.

The page reads the same feed as the badge next to **Alerts** in the sidebar, so a dismiss or a snooze brings the badge in line.

### Reading the feed

The header carries one number per quantity:

```
3 active of 5 · 2 snoozed · 1 of 2 critical
```

| Part | Meaning |
|---|---|
| `3 active of 5` | Rows visible under the current filters, of the organization's active total. The second number appears when a filter narrows the view. |
| `2 snoozed` | Alerts that are open but snoozed. The table hides them. |
| `1 of 2 critical` | Visible critical alerts, of the organization's critical total. |

The header also offers **Dismiss all (N)**. N counts every open alert, snoozed included.

### Filters

| Filter | Values |
|---|---|
| **Severity** | All, Critical, Warning, Info |
| **Source** | All, Prevented, System |
| **State** | All, Active, Digests |

**Prevented** alerts are the ones the gate stopped: a tool block, a budget block. **System** alerts are about the organization: a spend threshold, a killed workflow, a revoked key.

Severity and source are independent. A prevented incident can be critical, and a system event can be informational.

### A row

Each row shows the severity, what happened, the workflow it belongs to, and when it happened. Two actions:

| Action | Effect |
|---|---|
| **Snooze** | Hides the row for 1 hour, 24 hours, or 7 days. The row shows a countdown until it returns. |
| **Dismiss** | Closes the alert. It moves to the resolved list. |

Beneath the active list, a **Resolved today (N)** section holds the alerts dismissed during the current day. Dismissed rows carry no actions.

### What raises an alert

#### Threshold rules

Threshold rules are configured over the REST API. The control center has no editor for them: the **Notifications** page carries channels and event subscriptions, and nothing else.

Each rule has:

| Field | Meaning |
|---|---|
| **Name** | The label on the rule and in the alert it produces. |
| **Type** | What the rule watches. |
| **Threshold** | The value that triggers the rule. Spend rules use cents. Error-rate rules use a count of events. |
| **Window** | How far back the rule looks, in minutes. Defaults to 60. |
| **Severity** | `info`, `warning`, or `critical`. The severity of the alert the rule produces. Defaults to `warning`. |
| **Enabled** | Whether the rule fires at all. Defaults to on. |

The rule types are:

| Type | Watches |
|---|---|
| `daily_spend` | Spend over a day. |
| `hourly_spend` | Spend over an hour. |
| `error_rate` | The count of blocked and denied decisions in the window. |
| `per_key_spend` | Spend by one API key. |

A rule does not fire again within 15 minutes of its last firing. Each rule carries the last value it observed and when it last fired.

#### The budget ladder

Spending against a monthly budget raises alerts at fixed points:

| Spend | Severity |
|---|---|
| 80% of the budget | Warning |
| 95% of the budget | Warning |
| 100% of the budget | Critical |

#### Events

The event subscriptions on the **Notifications** page decide which events reach your channels. The full list is in [Notifications](#52-notifications).

### Configuring alerts

The **Set up alerts** button in the header opens the **Notifications** page, where you add the channels that receive the signals. The Alerts page is the read surface; Notifications is the configure surface. They share the same feed, so an alert that fires shows on both.

### API

| Method | Path |
|---|---|
| `GET` | `/api/v1/orgs/{org_id}/alerts` |
| `POST` | `/api/v1/orgs/{org_id}/alerts/{alert_id}/snooze` — body `{"hours": 24}`, clamped to 1–168 hours. |
| `POST` | `/api/v1/orgs/{org_id}/alerts/{alert_id}/dismiss` |
| `POST` | `/api/v1/orgs/{org_id}/alerts/dismiss-all` |

Dismiss-all covers the whole organization. There is no per-workflow bulk path, so cleaning up one workflow means dismissing its rows one by one.

The alert rules use their own paths. See [Notifications → API](#52-notifications).

### See also

- [Notifications](#52-notifications) — channels and event subscriptions
- [Budgets](#31-budgets) — the spend behind a spend alert
- [Policies](#22-policies) — what produces a blocked action


## 5.4 Team

The **Team** page lists everyone in the organization, every invite that has not been accepted yet, and what each person is allowed to do.

The team feature is on Starter and above. On Lite the sidebar link is
hidden and the page shows an upgrade prompt.

### Roles

There are four roles. They are ranked: every role can do what the roles below it can do.

| Role | Can do |
|---|---|
| **Viewer** | Read the control center: workflows, executions, traces, the audit log, and API keys. Export the audit log is not included — that needs Operator. |
| **Operator** | Everything a Viewer can do, plus pause and kill workflows, decide approvals, simulate a policy, and export the audit log. |
| **Admin** | Everything an Operator can do, plus create and edit workflows, policies, API keys and approval rules, edit the organization, manage MCP servers, and invite and remove members. |
| **Owner** | Everything an Admin can do, plus change a member's role, manage billing and SSO, and delete the organization. |

An organization always has at least one owner. The last owner cannot be demoted or removed.

Role-based access control arrives on Growth. On Starter an admin has no
effective authority — the owner carries it alone.

### Inviting someone

1. Open **Team** in the sidebar.
2. Enter the person's email address.
3. Pick the role they should have.
4. Send the invite.

The invite arrives by email and points at `https://nullrun.io/invite?token=<token>`. The link stays the same until the invite is accepted or revoked.

An invite is refused when:

- The address is already a member of the organization.
- An invite to that address is still pending.
- The seat quota is full.

### Pending invites

Invites that have not been accepted are listed under the members. Each row shows the address, the role, the invite link, and whether the last delivery attempt succeeded. You can resend the invite or revoke it.

A revoked invite stops working immediately.

### Seat quota

The header shows how many seats the organization uses against the plan's allowance. Members and pending invites count together, so an outstanding invite shows its cost before it is accepted.

When the quota is full, the invite button is disabled and the page links to **Billing & Plan** to buy more seats.

### Removing a member

Owners and admins can remove a member from the members list. Removing someone ends their sessions for the organization, so a live session cannot outlive the membership.

The last owner cannot be removed.

### Changing a role

Only an owner can change a member's role. Changing your own role is not possible, and the last owner cannot be demoted.

### Audit trail

On Growth and above, every invite, resend, revoke, role change, and removal is recorded in the audit log with the actor and the timestamp. Filter by the team action to reconstruct who did what.

The audit log is a plan feature. Lite and Starter have none.

### See also

- [Organization](#56-organization) — the organization's name, contact email, and DPA acceptance
- [Billing & Plan](#55-billing-plan) — where seats are bought
- [Audit log](#43-error-handling) — every team change leaves a row


## 5.5 Billing & Plan

The **Billing & Plan** page covers two things: the subscription and the plan. It lives under **Account** in the sidebar and has two tabs.

| Tab | Answers |
|---|---|
| **Billing** | Which plan, at what price, paid how, with which invoices. |
| **Plan** | How much of the plan is used, and what a different plan gives. |

The tab is part of the URL: `?tab=billing` or `?tab=plan`. **Billing** is the default. Every upgrade prompt in the control center opens `?tab=plan`, so a comparison comes before a payment.

### Plans and prices

| Plan | Monthly | Yearly | Per month, billed yearly |
|---|---|---|---|
| Lite | $0 | — | — |
| Starter | $29 | $278 | $23 |
| Growth | $99 | $950 | $79 |
| Scale | $299 | $2 870 | $239 |
| Enterprise | Contact sales | Contact sales | Contact sales |

Yearly billing costs 20 % less than twelve monthly payments. Lite is free and has no paid cycle.

### What a plan includes

A plan sets two things: the caps on what an organization may create, and the features it may use.

#### Caps

| Cap | Lite | Starter | Growth | Scale | Enterprise |
|---|---|---|---|---|---|
| Executions per month | 75 000 | 100 000 | 750 000 | 2 000 000 | Unlimited |
| Workflows | 3 | 8 | 50 | 200 | Unlimited |
| Policies | 3 | 10 | 25 | 150 | Unlimited |
| API keys | 10 | 15 | 100 | 350 | Unlimited |
| Seats | 1 | 3 | 10 | 75 | Unlimited |

An approval rule counts against the policy cap. A policy that carries its own approval rule counts once, as a policy.

#### Features

| Feature | Lite | Starter | Growth | Scale | Enterprise |
|---|---|---|---|---|---|
| Team | — | Yes | Yes | Yes | Yes |
| Alerts | — | Yes | Yes | Yes | Yes |
| RBAC | — | — | Yes | Yes | Yes |
| Human approvals | — | — | Yes | Yes | Yes |
| Audit log | — | — | Yes | Yes | Yes |
| Custom policies | — | — | Yes | Yes | Yes |
| Replay | — | — | Yes | Yes | Yes |
| SSO | — | — | — | Yes | Yes |
| History retention | 3 days | 7 days | 30 days | 90 days | Unlimited |

### The Lite trial

A new Lite organization gets Scale for 14 days. The Plan tab shows a countdown while the trial runs and a banner when it ends. The organization keeps its Lite plan and its Lite caps when the trial ends.

### The period

The executions counter runs over a period, and the period decides when the counter resets.

| Plan | The period |
|---|---|
| Lite | A rolling 30 days, anchored at the day the organization was created. |
| Paid | The billing cycle. Monthly or yearly, as billed. |

The Plan tab states the period under the Executions card: `rolling 30 days · resets in N days` for Lite, `resets on your billing day · in N days` for a paid plan.

### Reading the usage

The Plan tab opens with five quota cards, one per counter.

| Card | Counts | Resets |
|---|---|---|
| Executions | The decisions the organization took in the period. | On the period boundary. |
| Workflows | Saved workflows. | Never. |
| API keys | API keys. | Never. |
| Policies | Policies, plus the approval rules that count against the policy cap. | Never. |
| Team members | Members and pending invites. | Never. |

Each card shows the count, the cap, and the share used. A card with room left shows `N remaining`. A card on an unlimited cap shows `Unlimited`.

Deleting a workflow, a policy, or an API key frees its slot at once.

#### The at-risk banner

When the organization is on pace to reach its execution cap before the period ends, a banner states the number of days and links to a larger plan. Once the cap is reached, every execution is refused until the period resets.

### The plan comparison table

The Plan tab carries a table with one column per plan and one row per cap or feature: Price, Executions per month, Workflows, Policies, API keys, Seats, Team, RBAC, Human approvals, Audit log, History. The current plan's column is marked, and its button is disabled.

A **Monthly** / **Yearly** toggle sits above the table. It switches the price row between the monthly and the yearly figure.

### The Billing tab

#### The plan card

The card names the plan and the price.

| Plan | Reads |
|---|---|
| Lite | `Free • Forever`, with a **Free tier** chip. |
| Paid | `$29/mo` or `$278/yr`, with an **Active subscription** chip. |

A paid organization on the monthly cycle also gets a **Save 20 %** banner that links to the yearly prices.

#### Subscription details

| Field | Meaning |
|---|---|
| Status | `active`, `past_due`, `cancelled`, or `expired`. |
| Subscription ID | The short identifier of the subscription. |
| Started | The day the subscription began. |
| Next renewal | The day the current period ends. |

A Lite organization has no subscription, and the card reads **No active subscription**.

#### Payment method

The card shows the card on file as `Brand •••• last4`. **Update payment method** opens an email to support.

#### Invoices

The invoice table has one row per invoice.

| Column | Meaning |
|---|---|
| Date | When the invoice was issued. |
| Invoice | The invoice number. |
| Amount | The amount charged. |
| Status | `paid`, `open`, or `pending`. |
| Download | The invoice PDF. |

An organization with no invoices reads **No invoices yet**.

#### Contacting support

NullRun has no self-service customer portal. **Contact support** and **Update payment method** both open an email to `support@nullrun.io` with the details filled in.

### Changing the plan

**Upgrade plan** on the plan card opens the Plan tab, where each other tier carries its own button. An upgrade takes effect at once.

A downgrade to a plan with lower caps asks what to do with the objects that no longer fit. The preview lists every group that is over its new cap.

| Group | Choice |
|---|---|
| Workflows | Archive, Delete, or Keep. |
| Policies | Archive, Delete, or Keep. |
| Members | Archive. |
| Slack installs | Archive. |
| API keys | Revoke. |

A downgrade takes effect at the end of the current billing period. The Plan tab shows a banner with the date and the target plan until then.

### Plan identifiers

The plan identifiers on the wire are `lite`, `starter`, `growth`, `scale`, and `enterprise_unlimited`.

| Plan | Identifier |
|---|---|
| Lite | `lite` |
| Starter | `starter` |
| Growth | `growth` |
| Scale | `scale` |
| Enterprise | `enterprise_unlimited` |

Query the plan catalog by `enterprise_unlimited` for the Enterprise tier.

### API

The plan catalog is public. It needs no authentication.

| Method | Path |
|---|---|
| `GET` | `/api/v1/plans` |

### See also

- [Budgets](#31-budgets) — the money the plan pays for
- [Team](#54-team) — the seats the plan carries
- [Organization](#56-organization) — the workspace the plan belongs to


## 5.6 Organization

An **organization** is the workspace that holds everything: workflows, policies, approval rules, API keys, members, and spend. Every plan has one. Nothing on this page is gated.

The **Organization** page covers the organization's identity and its legal metadata. The plan and the seats live under [Billing & Plan](#55-billing-plan), and the people live under [Team](#54-team).

### Identity

| Field | What it does |
|---|---|
| **Name** | The display name in the control center, in email headers, and in audit rows. An owner can change it. |
| **Slug** | The URL-safe identifier. It is fixed for the life of the organization. |
| **Contact email** | The address billing and security messages go to. An owner can change it. |

Changing the contact email asks for a confirmation — a password or a two-factor code — before the change lands.

### Data Processing Agreement

The **DPA / Compliance** section shows whether the organization has accepted the current Data Processing Agreement.

The latest acceptance reads as a version and a date, for example `accepted v2026-06-25 on 2026-08-15`. An organization that has never accepted reads `not yet accepted`, and the section shows an **Accept DPA** button.

Every earlier acceptance stays visible underneath, with the version, the date, and how it was accepted:

| Method | Meaning |
|---|---|
| `in_product` | Accepted by clicking through the control center. |
| `signed_pdf` | Accepted offline and recorded by support. |
| `signup_checkbox` | Accepted on the sign-up form. |
| `checkout_step` | Accepted during checkout. |
| `sdk_api` | Accepted through the API. |

Accepting the same version twice is harmless. The organization keeps its first acceptance.

### Closing the organization

At the bottom of the page, the **Danger zone** closes the organization. Only an owner sees the button, and only when nobody else is a member.

To close an organization that still has other members, transfer ownership to one of them first. The request is refused with `ORG_HAS_MEMBERS` and the member count.

The confirmation asks you to type the organization name.

What closing the organization does:

- Marks the organization as closed. The workflows, executions, traces, policies, approval rules, alerts, API keys, memberships, and invites go with it.
- Ends the owner's session access to the organization. Other members lose access at the same time.
- Leaves the audit rows in place. They are kept for the retention window so a forensic question can still be answered afterwards.

#### The 60-day grace period

A closed organization can be restored. The grace period is 60 days.

| Action | Effect |
|---|---|
| **Restore** | Puts the organization back in front of the gate. The spend counters for the period survive, so a restored organization does not get a second allowance. |
| **Transfer ownership** | Hands the organization to another member. The remaining members keep access. |

When the grace period ends, the data is purged. The restore route is `POST /api/v1/orgs/{org_id}/restore`, and the ownership transfer is `POST /api/v1/orgs/{org_id}/transfer-ownership`.

### Audit trail

Every name change, contact email change, and DPA acceptance is recorded in the audit log with the actor and the timestamp. Closing the organization writes one row of its own.

### See also

- [Team](#54-team) — members, roles, and seats
- [Billing & Plan](#55-billing-plan) — the plan and the invoices
- [Profile settings](#57-profile-settings) — your own account
- [Audit log](#43-error-handling) — every organization change leaves a row


## 5.7 Profile settings

The **Profile settings** page is about you: the person signed in. It lives under **Profile** in the sidebar and is on every plan.

This is not the [Organization](#56-organization) page. The organization page edits the workspace. This page edits your account.

### Your details

| Field | What it does |
|---|---|
| **Display name** | How you appear in the control center and in audit rows. |
| **Email** | The address you sign in with and where notifications reach you. |
| **Avatar** | Your initials on a colour tile, or the avatar from your identity provider when you signed in with one. |

Changing the email asks for a confirmation — a password or a two-factor code — and sends a verification message to the new address. The address is not live until you click the link in it. A **Resend verification email** button appears while the address is unverified.

### Password

The password section appears when your account has a password. Signing up with an identity provider instead gives you a **Set password** action.

Changing a password asks for the current one. Every session ends, so every device has to sign in again.

### Two-factor authentication

Two-factor authentication adds a one-time code from an authenticator app to every sign-in.

| State | What you can do |
|---|---|
| **Not configured** | **Enable 2FA** shows a secret and a QR code. The first code confirms the enrolment. |
| **Enabled** | **Disable 2FA**, **Regenerate backup codes**, and **Regenerate secret**. Each asks for the current password and a fresh code. |

Enabling it asks for the current password before it issues a secret. Backup codes are shown once, at the point the first code confirms the enrolment. Only the number of codes left and the time of the last use stay visible.

If you lose the device, the recovery flow lets you disable two-factor authentication without it.

### Sessions

The session section shows:

- The last sign-in time and address.
- The number of active sessions.

Two actions:

| Action | Effect |
|---|---|
| **Sign out of all other devices** | Ends every session except the one you are using. |
| **Log out** | Ends the session in this browser. |

Signing out of the other devices is recorded in the audit log.

### Deleting your account

At the bottom of the page, the **Danger zone** deletes your account. The endpoint is `DELETE /api/v1/auth/account`.

The request asks for:

| Field | When it is needed |
|---|---|
| **Confirmation** | Your display name, typed exactly. Your email address is accepted as a fallback. |
| **Current password** | When your account has a password. |
| **Two-factor code** | When two-factor authentication is on. |
| **Ownership decision** | For every organization you own that has other members. |

An ownership decision has two shapes:

| Decision | What happens |
|---|---|
| Transfer | The organization moves to another member. |
| Delete and notify | The organization closes and its members are told. Their sessions end. |

Leaving a decision out is refused with `OWNERSHIP_DECISION_REQUIRED`, and the response lists the organizations with their members so you can decide in place.

What deletion does:

- Removes your account. You cannot sign in again.
- Ends every session you hold.
- Writes one audit row per organization you were a member of.

Organization data is untouched. Closing an organization is a separate action on the [Organization](#56-organization) page.

If a session cannot be ended, the whole operation stops and nothing is deleted. A half-finished deletion would leave live sessions pointing at an account that no longer exists.

### See also

- [Organization](#56-organization) — the workspace, its members, and closing it
- [Team](#54-team) — other people in the organization
- [Audit log](#43-error-handling) — every profile change leaves a row


# 6. How-to


## 6.1 Protect a LangGraph agent

The SDK attaches to LangGraph on its own. The attachment is installed
once per process — see [LLM frameworks](#65-llm-frameworks) for the
rule.

Import LangGraph before that happens. The patch wraps the `Pregel`
class, so a module that arrives after the attachment is never patched.

No vendor extra is needed. Install LangGraph and whatever chat model
client you use next to the SDK.

```bash title="shell"
pip install nullrun langgraph langchain-openai
```

### The wiring

```python title="langgraph_agent.py"
from langchain_openai import ChatOpenAI
from langgraph.graph import END, MessagesState, StateGraph

from nullrun import protect

llm = ChatOpenAI(model="gpt-4o-mini")


@protect
def chat(state: MessagesState):
    return {"messages": [llm.invoke(state["messages"])]}


graph = StateGraph(MessagesState)
graph.add_node("chat", chat)
graph.add_edge("chat", END)
graph.set_entry_point("chat")
app = graph.compile()

result = app.invoke({"messages": [{"role": "user", "content": "Hi"}]})
```

Every model call in the graph is cost-attributed to the workflow. The
`@protect` wrapper on the node is the gate boundary: the gateway
decides before the node body runs.

### When the automatic attachment misses the graph

Two cases need a different wiring:

- the graph is compiled in a worker thread, or
- LangGraph is imported after `init()` or after the first `@protect`
  call has already run.

Wrap the entry point instead of the graph. Every invocation passes
through that function, so the gate fires once per run:

```python title="langgraph_entrypoint.py"
from langchain_openai import ChatOpenAI
from langgraph.graph import END, MessagesState, StateGraph

from nullrun import protect

llm = ChatOpenAI(model="gpt-4o-mini")


def chat(state: MessagesState):
    return {"messages": [llm.invoke(state["messages"])]}


graph = StateGraph(MessagesState)
graph.add_node("chat", chat)
graph.add_edge("chat", END)
graph.set_entry_point("chat")
app = graph.compile()


@protect
def run_agent(prompt: str) -> str:
    result = app.invoke({"messages": [{"role": "user", "content": prompt}]})
    return result["messages"][-1].content
```

This also keeps `app` a plain compiled graph, so an `isinstance` check
against the graph class in your own code keeps working.

### See also

- [Quickstart](#14-quickstart)
- [LLM frameworks](#65-llm-frameworks) — the other supported frameworks
- [Examples → LangGraph](https://github.com/nullrunio/nullrun-examples/blob/master/examples/langgraph_basic.py)


## 6.2 Use with OpenAI Agents

Install the framework next to the SDK. There is no NullRun vendor extra
for it.

```bash title="shell"
pip install nullrun openai-agents
```

The SDK attaches to the framework on its own. The attachment is
installed once per process — see [LLM frameworks](#65-llm-frameworks)
for the rule. Import the `agents` package before that happens.

### The wiring

```python title="openai_agents_protect.py"
from agents import Agent, Runner

from nullrun import protect


@protect
def ask(prompt: str) -> str:
    agent = Agent(
        name="assistant",
        instructions="Answer in one sentence.",
    )
    result = Runner.run_sync(agent, prompt)
    return result.final_output


print(ask("What is the capital of France?"))
```

`@protect` runs the gate before the agent starts. The run is refused if
the workflow is out of budget, if a tool the agent calls is blocked, or
if the policy rate-limits the call.

The framework hook reports the token counts of every model call the
agent makes, so the spend lands on the workflow without any manual
tracking.

### See also

- [LLM frameworks](#65-llm-frameworks) — the other supported frameworks
- [Examples → OpenAI Agents](https://github.com/nullrunio/nullrun-examples/blob/master/examples/openai_agents_basic.py)


## 6.3 Use CrewAI

Install CrewAI next to the SDK. There is no NullRun vendor extra for
it.

```bash title="shell"
pip install nullrun crewai
```

The SDK attaches to CrewAI on its own. The attachment is installed once
per process — see [LLM frameworks](#65-llm-frameworks) for the rule.
Import the `crewai` package before that happens.

### The wiring

```python title="crewai_crew.py"
from crewai import Agent, Crew, Task
from nullrun import protect

researcher = Agent(
    role="Researcher",
    goal="Answer the question",
    backstory="Concise and accurate.",
)

task = Task(
    description="What does NullRun do?",
    agent=researcher,
    expected_output="Two sentences.",
)

crew = Crew(agents=[researcher], tasks=[task])


@protect
def run_crew() -> str:
    return str(crew.kickoff())


print(run_crew())
```

`@protect` runs the gate once, at the start of the crew run. The run
is refused if the workflow is out of budget, if the policy rate-limits
the call, or if the workflow is paused or killed.

CrewAI tool calls are reported as span events. They are not
evaluated against the tool policy on their own.

### What the SDK reports

| Source | What it reports |
|---|---|
| The CrewAI event bus | Crew, agent, task, model, and tool lifecycle events |
| `crew.usage_metrics` | One LLM cost row per model, read after the run returns |

The event bus path needs CrewAI 1.15 or newer. On an older release the
lifecycle events are skipped and the usage totals still arrive.

### See also

- [LLM frameworks](#65-llm-frameworks)
- [Multi-agent orchestration](#68-multi-agent-orchestration)
- [Quickstart](#14-quickstart)


## 6.4 Use with FastAPI

Install FastAPI next to the SDK.

```bash title="shell"
pip install nullrun fastapi uvicorn
```

`nullrun.integrations.fastapi.install(app)` registers the NullRun
exception handlers and the kill middleware on your app. Every refusal
the gate raises becomes a JSON response with an HTTP status.

```python title="fastapi_app.py"
import nullrun
from fastapi import FastAPI
from nullrun.integrations.fastapi import install

nullrun.init(api_key="nr_live_replace_me")

app = FastAPI()
install(app)


def run_agent(message: str) -> str:
    """Your agent call goes here."""
    return message


@app.post("/chat")
@nullrun.protect
def chat(message: str) -> dict:
    return {"reply": run_agent(message)}
```

### What `install()` registers

| Registration | Handles | HTTP |
|---|---|---|
| Exception handler for `NullRunDecision` | Budget, tool block, loop, pause, chain errors | Per `error_code` |
| Exception handler for `NullRunInfrastructureError` | Transport, backend, auth, config, rate limit | `503` |
| ASGI middleware `NullRunMiddleware` | `WorkflowKilledInterrupt` | `503` |

The kill middleware sits outside the exception handler chain. A kill
that fires after the response has started cannot be rewritten, so the
middleware re-raises it and the connection drops.

### Status mapping for decisions

The integration reads `error_code` on the exception and picks a
status.

| `error_code` | HTTP | Meaning |
|---|---|---|
| `NR-B004` | `429` | Budget exhausted |
| `NR-L001` | `429` | Loop detected |
| `NR-R001` | `429` | Rate limited |
| `NR-T001` | `403` | Tool blocked |
| `NR-X001` | `403` | Generic block |
| `NR-W003` | `503` | Workflow paused |
| Any other decision code | `429` | Default |

Every infrastructure error maps to `503`. A gateway 429 arrives as
`RateLimitError`, which is an infrastructure error, so it lands on
`503` and not on `429`. A decision that carries `NR-R001` — the
legacy block path, where the SDK reads the reason text and no wire
code was sent — is a decision, and lands on `429`.

The response carries a `Retry-After` header when the exception has a
`retry_after` value (rate limit) or a `resume_after` value (pause).

### Response body

```json
{
  "error_code": "NR-B004",
  "user_message": "You've reached the usage limit for this conversation. Please try again later.",
  "category": "decision",
  "retryable": false
}
```

| Field | Type | Meaning |
|---|---|---|
| `error_code` | string | Stable machine-readable code |
| `user_message` | string | End-user-safe text. Safe to render in a UI |
| `category` | `decision`, `infrastructure`, `killed` | Coarse class for client branching |
| `retryable` | bool | Mirrors the exception's own flag |

The kill response has no `retryable` field.

### Mapping one endpoint yourself

Use your own handler when an endpoint needs different wording or a
different status.

```python title="custom_mapping.py"
from fastapi import HTTPException
from nullrun import (
    NullRunDecision,
    NullRunInfrastructureError,
    WorkflowPausedException,
    format_user_message,
)


def run_agent(message: str) -> str:
    """Your agent call goes here."""
    return message


@app.post("/chat")
@nullrun.protect
def chat(message: str) -> dict:
    try:
        return {"reply": run_agent(message)}
    except WorkflowPausedException as exc:
        # .status_code is absent here. .resume_after carries the wait.
        raise HTTPException(
            status_code=503,
            detail={
                "message": format_user_message(exc),
                "code": exc.error_code,
            },
            headers={"Retry-After": str(int(exc.resume_after or 0))},
        )
    except NullRunDecision as exc:
        # .status_code is absent on some decision classes, so read it
        # defensively.
        raise HTTPException(
            status_code=getattr(exc, "status_code", None) or 403,
            detail={
                "message": format_user_message(exc),
                "code": exc.error_code,
                "retryable": exc.retryable,
            },
        )
    except NullRunInfrastructureError as exc:
        raise HTTPException(
            status_code=getattr(exc, "status_code", None) or 503,
            detail={"message": format_user_message(exc), "code": exc.error_code},
        )
```

Not every decision carries a `status_code`. `WorkflowPausedException`
and `WorkflowKilledInterrupt` have no such attribute, and a
client-side `NullRunBlockedException` carries `None`. Read it with
`getattr` and supply your own fallback.

### Per-deployment wording

Brand the message for one error code with `set_user_message`:

```python
import nullrun

nullrun.set_user_message(
    "NR-B004",
    "This workflow is out of budget. Raise the cap in the control center.",
)
```

### Two things to know

**Handler precedence follows the class hierarchy.** Starlette looks up
a handler by walking the exception's class hierarchy. A handler you
register for `NullRunError` therefore loses to the handlers
`install()` registers for `NullRunDecision` and
`NullRunInfrastructureError`. Register your own handler for one of
those two classes if you want to take it over.

**The kill is an `Exception`.** `WorkflowKilledInterrupt` derives from
`NullRunError`, so a blanket `except Exception:` in your agent code
swallows an operator kill. Catch `WorkflowKilledInterrupt` first and
re-raise.

```python title="kill_handling.py"
from nullrun import WorkflowKilledInterrupt


def run_agent(message: str) -> str:
    """Your agent call goes here."""
    return message


@app.post("/chat")
@nullrun.protect
def chat(message: str) -> dict:
    try:
        return {"reply": run_agent(message)}
    except WorkflowKilledInterrupt:
        raise
```

### See also

- [Quickstart](#14-quickstart)
- [Errors](#75-error-codes)


## 6.5 LLM frameworks

The SDK attaches to the HTTP client and to the agent frameworks it
finds installed. The attachment is installed once per process: at
`init()`, or at the first `@protect` call if you never call `init()`.
Import the framework before that point — a package that arrives later
is never patched.

Two layers, and they do different work:

| Layer | What it does |
|---|---|
| Cost tracking | Reports the token counts of every LLM call |
| Gate | Refuses a call that breaks budget, policy, or the control plane |

Cost tracking runs on its own. `@protect` is what turns a tracked call
into a gated one.

### Providers

Provider coverage is keyed on the request host. The SDK never imports
a vendor package to cover it, so there is no vendor extra to install.

| Host | Provider |
|---|---|
| `api.openai.com` | OpenAI |
| `openai.azure.com` | Azure OpenAI |
| `api.anthropic.com` | Anthropic |
| `api.mistral.ai` | Mistral |
| `generativelanguage.googleapis.com` | Google Gemini |
| `api.cohere.ai` | Cohere |
| `bedrock-runtime.amazonaws.com` | AWS Bedrock |

A sub-domain of one of these hosts matches too. The OpenAI and
Mistral responses share one shape, so one extractor covers both.

The SDK reports token counts. The gateway prices the call from the
model name and the org's pricing policy.

### Frameworks

Each framework hook is a no-op when the package is not installed.

| Package | What the hook covers |
|---|---|
| `httpx` | Every HTTP client built on it, including the OpenAI and Anthropic SDKs |
| `requests` | Every client built on the `requests` library |
| `langchain-core` (`langchain_core`) | Chat-model calls, including in-memory mock providers |
| `langgraph` | Compiled graphs, on every run mode |
| `openai-agents` (`agents`) | The runner, with the token counts of each model call |
| `crewai` | Crew, agent, task, model, and tool lifecycle events, plus the run's usage totals |
| `llama-index` (`llama_index`) | LLM chat completions and tool calls |
| `autogen-agentchat` (`autogen_agentchat`) | Agent lifecycle events and the OpenAI client usage |

Install the SDK once, then install the frameworks you use:

```bash title="shell"
pip install nullrun langgraph langchain-openai openai-agents crewai
```

### A runnable example

```python title="tracked_call.py"
from langchain_openai import ChatOpenAI
from nullrun import protect

llm = ChatOpenAI(model="gpt-4o-mini")


@protect
def ask(prompt: str) -> str:
    return llm.invoke(prompt).content


print(ask("What is the capital of France?"))
```

The framework hook reports the token counts of the call inside
`ask`. The `@protect` wrapper gates it.

### When the SDK cannot see the call

| Symptom | Cause | Fix |
|---|---|---|
| No cost shows up for a provider | The host is not in the table above | Report the call by hand |
| No cost shows up for a custom client | The client does not use `httpx` or `requests` | Report the call by hand |
| The call is tracked twice | A manual report sits next to an automatic one | Drop the manual report |

Reporting a call by hand means calling `runtime.track_llm(...)`. See
[Manual cost and event tracking](#610-manual-cost-event-tracking).

Do not report a call the SDK already sees. The two reports add up.

### See also

- [Protect a LangGraph agent](#61-protect-a-langgraph-agent)
- [Use with OpenAI Agents](#62-use-with-openai-agents)
- [Use with CrewAI](#63-use-crewai)
- [Manual cost and event tracking](#610-manual-cost-event-tracking)


## 6.6 Set a hard cost cap

A cost cap stops an agent from spending past a number you chose. The cap
is per workflow and per billing period.

The gateway enforces the cap. The SDK asks the gateway before every
protected call and books the real cost after the call returns.

### Set the cap

Two paths set the same cap. Use one or both — the gateway applies the
lower of the two.

**In the control center:** open **Governance → Policies**, choose **New
policy**, set the type to **Budget**, set the scope to the workflow, and
fill **Max cost (USD/month)**. The field takes dollars. `$50.00` is
`5000` cents.

**Over the HTTP API:** `PATCH` the workflow:

```bash title="shell"
ORG_ID=8a3b1c7d-0000-4000-8000-000000000000
WORKFLOW_ID=1f2e3d4c-0000-4000-8000-000000000000
API_KEY=nr_live_replace_me

curl -sS -X PATCH \
  "https://api.nullrun.io/api/v1/orgs/$ORG_ID/workflows/$WORKFLOW_ID" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"budget_cents": 500}'
```

`budget_cents` is the only field the request needs. A cap of `0` on the
workflow means no per-workflow cap — the call passes through to the
organization cap.

The key must belong to the organization in the path and must be bound to
a user. The caller needs the Owner role, or the Admin role on a plan
that includes role-based access control. A control center session works too:
replace the `X-API-Key` header with `Authorization: Bearer
$SESSION_TOKEN`. See
[HTTP API → Authentication](#73-http-api).

See [Policies → BudgetLimit](#22-policies)
for the policy fields and
[Budgets](#31-budgets) for the period and the counter.

### Run against the cap

```python title="budgeted_run.py"
import nullrun
from nullrun import init, protect

init(api_key="nr_live_replace_me")


def call_model(question: str) -> str:
    """Your model call goes here."""
    return question


@protect
def answer(question: str) -> str:
    return call_model(question)
```

| Refusal | Exception | `error_code` |
|---|---|---|
| Budget cap reached | `NullRunBudgetError` | `NR-B004` |
| Tool blocked by policy | `NullRunToolBlockedError` | `NR-T001` |

Both are subclasses of `NullRunBlockedException`, so one
`except NullRunBlockedException` clause catches both. The typed subclass
carries the specific `error_code`. See [Errors](#75-error-codes).

### How the cap is checked

Each protected call runs the gate first:

1. The gateway reserves the projected cost of the call.
2. If the reservation crosses the cap, the call is refused and nothing
   is reserved.
3. After the call returns, the gateway books the real cost against the
   reservation.

The real cost may exceed the reservation by a small fixed amount. A
booking above the reservation plus that amount is rejected. The commit
answers `422` with the wire code `CONSUME_OVERBUDGET`, and the SDK
raises `NullRunConsumeOverbudgetError` (`NR-O001`). See
[Budgets → Reserve and consume](#31-budgets).

The SDK does not compute the cost. It sends the model and a token
estimate to the gate. After the call it sends the token counts the
provider reported. The gateway prices the call.

### Soft mode

A policy set to **Soft** lets the agent run past the cap while a chain
is active, up to an overdraft limit. Soft mode needs all three of: the
policy sets `enforcement_mode` to `Soft`, an active chain exists, and
the projected cost stays inside the overdraft limits. When one of them
is missing, the budget behaves as Hard. See
[Policies → BudgetLimit extra fields](#22-policies)
and [Policies → Soft mode requirements](#22-policies).

### See also

- [Budgets](#31-budgets) — periods, spend, and the reserve
- [Errors](#75-error-codes) — the full exception catalog
- [Examples → cost cap demo](https://github.com/nullrunio/nullrun-examples/blob/master/examples/cost_cap_demo.py)


## 6.7 Run multiple agents

Two rules shape every deployment:

1. An API key binds to one workflow.
2. The SDK holds one runtime per process.

So N workflows on one host means N processes. This page shows the three
patterns that cover real deployments.

For sub-agents that share one workflow inside one process, see
[Multi-agent orchestration](#68-multi-agent-orchestration).

### Pattern 1 — one process per key

Each workflow gets its own process, its own environment variable, and
its own log stream. Any supervisor works: systemd, Docker Compose, or
Kubernetes.

The rule does not change with the supervisor. Give each process its own
`NULLRUN_API_KEY`:

```bash title="service.env"
NULLRUN_API_KEY=nr_live_replace_me
```

The control center then shows separate spend per workflow, kill and pause
work independently, and you can restart one without touching the
others.

### Pattern 2 — fan out inside one container

Use a process pool when one entrypoint has N workflows to run. Each
child builds its own runtime from its own key.

```python title="fanout.py"
import multiprocessing as mp
import os

from nullrun import protect


def call_model(text: str) -> str:
    """Your model call goes here."""
    return text


def _run_one(job: tuple[str, str]) -> str:
    key, prompt = job
    # The runtime is created lazily on the first @protect call, so the
    # key has to be in the environment before that happens.
    os.environ["NULLRUN_API_KEY"] = key

    @protect
    def step(text: str) -> str:
        return call_model(text)

    return step(prompt)


def fan_out(jobs: list[tuple[str, str]]) -> list[str]:
    # "spawn" gives every child a fresh interpreter and a fresh runtime.
    ctx = mp.get_context("spawn")
    with ctx.Pool(processes=len(jobs)) as pool:
        return pool.map(_run_one, jobs)
```

Use the `spawn` start method. The `fork` method copies the parent's
memory into the child. If the parent already created a runtime, the
child inherits it and reports to the parent's workflow with the parent's
key.

### Pattern 3 — one subprocess per request

Route at the process level when one CLI or API server handles requests
for many workflows.

```python title="router.py"
import os
import subprocess


def run_workflow(key: str, prompt: str) -> str:
    result = subprocess.run(
        ["python", "agent.py", prompt],
        env={**os.environ, "NULLRUN_API_KEY": key},
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
    )
    return result.stdout
```

Each subprocess is its own interpreter with its own runtime, so the
isolation is automatic. The price is process startup on every request.
For a steady stream of requests, Pattern 2 keeps workers warm.

### Why not several keys in one process

The runtime is a process-wide singleton. A second `init()` call shuts
the first runtime down, so one process cannot hold two keys at once.

The failure mode of forcing it is interleaved events: calls land on the
workflow of whichever key the runtime happens to hold, and the control center
shows a spend that belongs to no single workflow.

### One workflow across many processes

Every process that holds the same key reports to the same workflow.
Several workers with the same key produce one workflow record with the
combined spend.

### See also

- [Multi-agent orchestration](#68-multi-agent-orchestration) — sub-agents
  inside one process
- [Concepts → API keys](#25-api-keys) — how a key binds to a
  workflow
- [Configuration → env vars](#15-configuration)


## 6.8 Multi-agent orchestration

An orchestrator delegates to sub-agents: a LangGraph supervisor, a
CrewAI crew, an OpenAI Agents runner with handoffs, or a hand-written
loop.

This page covers sub-agents inside **one process**. For running
separate workflows on separate keys, see
[Run several agents on one host](#67-run-multiple-agents).

### One workflow block for the whole tree

Wrap the orchestrator in a single `workflow()` block. The block gives
every call inside it the same trace.

```python title="langgraph_orchestrator.py"
from typing import TypedDict

from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from nullrun import protect, workflow

llm = ChatOpenAI(model="gpt-4o-mini")


class State(TypedDict):
    topic: str
    research: str
    draft: str


@protect
def research_node(state: State) -> State:
    out = llm.invoke(f"Research {state['topic']}")
    return {"research": out.content}


@protect
def writer_node(state: State) -> State:
    out = llm.invoke(f"Write a draft using: {state['research']}")
    return {"draft": out.content}


with workflow("research-supervisor"):
    graph = StateGraph(State)
    graph.add_node("research", research_node)
    graph.add_node("writer", writer_node)
    graph.add_edge("research", "writer")
    graph.add_edge("writer", END)
    graph.set_entry_point("research")
    app = graph.compile()
    app.invoke({"topic": "LLM cost trends"})
```

The gate runs per node, because each node is `@protect`-wrapped. One
wrapper around `app.invoke()` would gate the whole graph once.

### The budget comes from the API key

The cap is always the budget of the workflow the API key is bound to.
The gateway derives that binding from the key. It does not take the
workflow name from the SDK.

So a `workflow()` block does not open a second budget pool. It scopes
the labels on the events emitted inside it.

Use one `workflow()` block per process. If you want a separate budget
per sub-agent, give each sub-agent its own API key and its own
process.

### Naming the sub-agents

`agent()` and `span()` label the work inside the tree without opening a
new budget.

```python title="labelled_subagents.py"
from typing import TypedDict

from langchain_openai import ChatOpenAI

from nullrun import agent, protect, span

llm = ChatOpenAI(model="gpt-4o-mini")


class State(TypedDict):
    topic: str
    research: str


@protect
def research_node(state: State) -> State:
    with agent("researcher"):
        with span("search"):
            out = llm.invoke(f"Research {state['topic']}")
    return {"research": out.content}
```

### Kill reaches the whole tree

An operator hits **Kill** in the control center. The control plane pushes the
new state to every SDK client in the organization. A client raises at
its next protected call on the killed workflow.

The exception depends on the function type. A sync function raises
`NullRunBlockedException` with `error_code` `NR-W002`. A coroutine
raises `WorkflowKilledInterrupt`. The async wrapper leaves the original
exception alone so an async framework can cancel the task on the type
it expects. See
[Control plane → Sync and async behave differently](#44-control-plane-websocket)
for the full matrix.

Catch the kill by name and re-raise it:

```python title="kill_handling.py"
from nullrun import WorkflowKilledInterrupt


async def run_orchestration() -> None:
    try:
        await agent_step("do something")
    except WorkflowKilledInterrupt:
        # The operator killed the workflow. Stop the tree and re-raise.
        raise


async def agent_step(prompt: str) -> None:
    """Your agent work goes here."""
```

### Common pitfalls

| Pitfall | Symptom | Fix |
|---|---|---|
| No `workflow()` block around the orchestrator | Every protected call is its own trace | Wrap the tree in one block |
| A nested `workflow()` per sub-agent | Each block relabels the events inside it | Use `agent()` and `span()` for labels |
| One key per sub-agent | Every sub-agent needs its own process and its own key | Use one key for the orchestrator |
| A broad `except Exception` that does not re-raise | The kill is swallowed and the agent keeps running | Catch `WorkflowKilledInterrupt` first |

### See also

- [Run several agents on one host](#67-run-multiple-agents) — separate processes
  and separate keys
- [Workflow context](#41-workflow-context) — what `workflow()` scopes
- [Chain context](#41-workflow-context) — soft mode for
  multi-step orchestrations
- [Use with LangGraph](#61-protect-a-langgraph-agent) — the single-agent wiring


## 6.9 Stream responses

Two things make streaming different from a normal call: the response
arrives in pieces, and the run can take longer than a single gate
decision covers.

### Protect the call, not the generator

`@protect` wraps a function call. A function that yields is not a call
that finishes: the body runs later, when the caller iterates. The SDK
has no generator support, so a protected generator runs its body
outside the gate.

Protect the function that opens the stream instead. The gate runs when
the stream is created:

```python title="stream_answer.py"
import uuid

from openai import AsyncOpenAI
from nullrun import chain, protect

client = AsyncOpenAI()


@protect
async def open_stream(prompt: str):
    return await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        stream=True,
    )


async def answer(prompt: str):
    chain_id = str(uuid.uuid4())
    with chain(chain_id, op="start"):
        stream = await open_stream(prompt)
        async for chunk in stream:
            yield chunk.choices[0].delta.content or ""
```

The alternative is to protect each step of the loop. That gives the
gate one decision per chunk, which costs a round trip per chunk.

### Keep the chain alive

A chain closes after five minutes without a protected call, or after one
hour of chain lifetime.

Send a heartbeat while the stream runs. `ping_chain` schedules them on
a wall-clock timer and returns a callable that stops the schedule:

```python title="stream_with_heartbeat.py"
import uuid

from openai import AsyncOpenAI
from nullrun import chain, get_runtime, protect

client = AsyncOpenAI()


@protect
async def open_stream(prompt: str):
    return await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        stream=True,
    )


async def answer(prompt: str):
    runtime = get_runtime()
    chain_id = str(uuid.uuid4())
    with chain(chain_id, op="start"):
        stop = runtime.ping_chain(chain_id)
        try:
            stream = await open_stream(prompt)
            async for chunk in stream:
                yield chunk.choices[0].delta.content or ""
        finally:
            stop()
```

`ping_chain` sends a heartbeat every 30 seconds by default. The
interval must stay between 10 and 120 seconds.

#### Chain heartbeat

The interval is wall-clock, not chunk-based. One chunk per minute still
gets a heartbeat, and a fast stream does not flood the server.

A failed heartbeat is logged and ignored. The chain then closes when
its idle window runs out.

### What the SDK does with the chunks

The HTTP client you use decides how the chunks reach your code.

| HTTP client | When the chunks reach your code | Cost tracked for you |
|---|---|---|
| `httpx` | After the whole body has been read | Yes |
| `requests` | As they arrive | No |

The OpenAI and Anthropic SDKs are built on `httpx`. The SDK reads the
body in full so it can read the usage block that arrives in the last
chunk. The chunks then reach your code together.

The `requests` path leaves a streamed body alone, so the chunks arrive
in real time. The SDK cannot read the usage block, so it reports the
call as untracked and the cost stays at zero.

### Report a stream by hand

Report the call yourself when the SDK does not see it. Use
`stream_options={"include_usage": True}` so the last chunk carries the
usage block:

```python title="track_stream.py"
from openai import OpenAI

from nullrun import get_runtime

client = OpenAI()


def stream_with_cost(prompt: str):
    stream = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        stream=True,
        stream_options={"include_usage": True},
    )
    final = None
    for chunk in stream:
        final = chunk
        yield chunk.choices[0].delta.content or ""

    usage = getattr(final, "usage", None)
    if usage:
        runtime = get_runtime()
        runtime.check_workflow_budget(model="gpt-4o-mini")
        runtime.track_llm(
            input_tokens=usage.prompt_tokens,
            output_tokens=usage.completion_tokens,
            model="gpt-4o-mini",
        )
```

A manual report needs a budget check in the same scope. The SDK drops
an `llm_call` report that has no reservation, and logs the drop.

A report the SDK already made adds the tokens a second time. Report a
call once.

### Kill during a stream

An operator kill reaches the SDK over the control-plane connection. It
surfaces at the next protected call. A coroutine raises
`WorkflowKilledInterrupt`. A sync function raises
`NullRunBlockedException` with `error_code` `NR-W002`. See
[Control plane → Sync and async behave differently](#44-control-plane-websocket)
for the full matrix.

A chunk loop over an open stream holds no protected call, so the kill
lands on the next stream you open. Catch it by name and close the
stream:

```python title="kill_handling.py"
from nullrun import WorkflowKilledInterrupt


async def answer(prompt: str):
    stream = None
    try:
        stream = await open_stream(prompt)
        async for chunk in stream:
            yield chunk.choices[0].delta.content or ""
    except WorkflowKilledInterrupt:
        if stream is not None:
            await stream.close()
        raise
```

### See also

- [Chain context](#41-workflow-context)
- [Errors → SDK exception hierarchy](#75-error-codes)
- [Manual cost and event tracking](#610-manual-cost-event-tracking)


## 6.10 Manual cost / event tracking

Auto-instrumentation books most LLM calls for you. The SDK watches the
HTTP client and the framework hooks, reads the token counts out of the
provider response, and reports them.

Reach for the runtime's tracking methods when the SDK cannot see the
call:

- your LLM client does not use `httpx`, for example a raw socket client
  or an offline batch job reading cached completions;
- you proxy the call, so the SDK reads your proxy's response instead of
  the provider's;
- you call something that is not an HTTP request, such as a database
  query or a custom side-effecting function;
- you want a business event in the record, such as a milestone or a
  variant assignment.

If your client is the standard OpenAI, Anthropic, Gemini, Cohere,
Mistral, or Bedrock SDK, do not report the call by hand.
Auto-instrumentation already fires, and a second report double-counts
the tokens.

### The three methods

They live on the runtime instance. Reach the runtime with
`nullrun.get_runtime()`.

There is no package-level `nullrun.track_llm`, `nullrun.track_tool`, or
`nullrun.track`. Those names do not exist. The public package surface is
the `@protect` decorator plus the lifecycle and error helpers. See
[SDK API → Package surface](#71-sdk-api).

| Method | Purpose | Required fields |
|---|---|---|
| `runtime.track_llm(input_tokens, output_tokens=0, *, model=None, latency_ms=None, metadata=None)` | Report an LLM call | `input_tokens`; `model` required |
| `runtime.track_tool(tool_name, duration_ms=None, *, is_retry=False, metadata=None)` | Report a tool call | `tool_name` |
| `runtime.track(event)` | Report an arbitrary event | `type` |

`runtime.track_event(event_type, **kwargs)` is the same thing with the
event type as the first argument.

### An LLM report needs a reservation

The gateway books a cost against a reservation. The SDK drops an
`llm_call` event that has no reservation in scope, and logs a warning
that names the event type and the workflow. Nothing is billed.

Two ways to get a reservation:

| Way | What it does |
|---|---|
| Wrap the call in `@protect` | Runs the budget check and the tool policy, then hands the body a reservation |
| Call `runtime.check_workflow_budget()` first | Runs the budget check only |

A call the SDK cannot see therefore costs nothing until you report it
inside one of those two scopes. Report it outside them and the spend
total stays too low, so the cap fires late.

### Example

```python title="track_custom.py"
import nullrun
from nullrun import protect


@protect
def run_step(response, elapsed_ms: int):
    runtime = nullrun.get_runtime()
    runtime.track_llm(
        input_tokens=response.usage.prompt_tokens,
        output_tokens=response.usage.completion_tokens,
        model="custom-llm-v1",
        latency_ms=elapsed_ms,
        metadata={"vendor": "internal"},
    )
    runtime.track_event("agent.milestone", step="research_complete")
```

`@protect` reports the tool call itself, under the function name. Call
`runtime.track_tool` only for a tool the SDK cannot see.

`@protect` uses the function name as the tool name. Name the function
after the tool the policy matches:

```python title="gated_tool.py"
from nullrun import protect


@protect
def send_email(to: str, body: str) -> None:
    ...
```

A tool call that never passes through `@protect` is never checked
against a blocked-tool rule. The manual report never blocks it either.

### Tracking is reporting, not enforcement

`track_tool` records the call. It does not run the tool policy.

The policy engine runs on the gate, which `@protect` triggers.

### Caveats

- **The model name is required.** The gateway prices the call from the
  model name and the token counts. An `llm_call` event with no `model`
  field is tagged by the SDK, and the gateway refuses the report with
  `422`.
- **Buffering.** LLM events go to the gateway one at a time. Tool events
  and span events go out in batches, flushed on a timer or when the
  batch fills. `init()` registers a shutdown hook that drains the
  buffer, so a clean process exit never loses events.
- **Dedupe covers `track_event` only.** The SDK gives a `track_event` a
  content fingerprint and drops a repeat of the same event.
  `track_llm` and `track_tool` carry no fingerprint, so two calls with
  the same payload are two events.
- **Control-plane checks.** A tracking call reads the workflow state. A
  paused or killed workflow raises out of `track_llm` as well as out of
  `@protect`.

### See also

- [SDK API → Manual tracking](#71-sdk-api)
- [LLM frameworks](#65-llm-frameworks) — which providers the SDK sees on
  its own


## 6.11 CI / CD integration

Wire NullRun into the build so a policy mistake is caught before it
reaches production.

The check drives the real SDK against a real gateway with synthetic
token counts. No LLM provider is called, so the job costs nothing and
spends no provider tokens.

### The load tool

The examples repo ships a CLI for this:
[`synthetic_sdk_load.py`](https://github.com/nullrunio/nullrun-examples/blob/master/tools/synthetic_sdk_load.py).

It runs the public SDK path. Each call sends a gate request, then a
tracking request with random token counts.

| Flag | Meaning |
|---|---|
| `--interval` | Seconds between call launches |
| `--duration` | Duration cap in seconds |
| `--requests` | Request cap. `0` uses the duration cap only |
| `--workers` | Maximum concurrent calls |
| `--model` | Model name reported for the synthetic calls |
| `--min-tokens`, `--max-tokens` | Range the random token counts fall in |
| `--seed` | Seed for the random generator |
| `--dry-run` | Schedule locally without sending anything |
| `--yes` | Skip the confirmation prompt |

Exit code:

| Code | Meaning |
|---|---|
| `0` | Every call succeeded |
| `1` | At least one call failed, or the API key is missing |
| `2` | The confirmation was declined |

### GitHub Actions

```yaml title=".github/workflows/pre-prod.yml"
name: pre-prod-validation

on:
  pull_request:
    branches: [master]

jobs:
  nullrun-smoke:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    env:
      NULLRUN_API_URL: ${{ secrets.NULLRUN_PRE_PROD_URL }}
      NULLRUN_API_KEY: ${{ secrets.NULLRUN_PRE_PROD_KEY }}
    steps:
      - uses: actions/checkout@v4

      - name: Install the SDK and the load tool
        run: |
          git clone --depth 1 https://github.com/nullrunio/nullrun-examples.git
          pip install nullrun

      - name: 1. Health check
        run: curl -fs "${NULLRUN_API_URL}/health/live"

      - name: 2. Capabilities probe
        run: |
          curl -fs "${NULLRUN_API_URL}/api/v1/capabilities" | python -c '
          import json, sys
          payload = json.load(sys.stdin)
          caps = payload.get("capabilities") or {}
          flags = (
              "server_minted_execution_id",
              "per_execution_reservations",
              "heartbeat_time_based",
          )
          missing = [f for f in flags if not caps.get(f)]
          assert not missing, "gateway is not ready: " + ", ".join(missing)
          lo = payload["min_protocol_version"]
          hi = payload["max_protocol_version"]
          assert lo <= 4 <= hi, f"gateway accepts protocol {lo}..{hi}, the SDK sends 4"
          '

      - name: 3. Synthetic load
        working-directory: nullrun-examples
        run: |
          set -euo pipefail
          python tools/synthetic_sdk_load.py \
            --interval 0.05 \
            --workers 10 \
            --requests 200 \
            --model gpt-4o-mini \
            --yes
```

`set -euo pipefail` makes the step fail on the first error. The exit
code of the load tool is the CI gate.

### The checks

**The health check** confirms the gateway answers. It reads no
organization data, so it needs no key.

**The capabilities probe** confirms the gateway speaks the wire
contract the SDK needs. Three flags must be true:
`server_minted_execution_id`, `per_execution_reservations`, and
`heartbeat_time_based`. The endpoint sits outside the protocol-gated
routes, so it answers without the protocol header.

The SDK sends `X-NULLRUN-PROTOCOL: 4`. The gateway advertises the
range it accepts as `min_protocol_version` and `max_protocol_version`.

**The synthetic load** runs the gate for real. It catches:

- a budget cap that is too tight for the traffic
- a rate limit that refuses the traffic
- a key that is missing, revoked, or bound to another organization
- a policy that refuses every call

### What the load does not catch

- **Real spend.** The token counts are random. Use a staging workflow
  with a small cap for a cost estimate.
- **Pricing for a model.** Check the cost view in the control center after
  one real call.
- **Kill and pause.** The synthetic load does not exercise the
  control-plane paths. Trigger them by hand during a release
  checklist.
- **Your tool names.** The load tool gates a function of its own. It
  tells you the tool policy refuses calls, not which of your tool
  names it refuses.

### The manual step

An approval flow needs a human to click **Approve**. Run it by hand on
every release candidate. See
[Human approval](#32-human-approval).

### Common failures

| Symptom | Meaning | Fix |
|---|---|---|
| The tool exits `1` and prints a report to stderr | `NULLRUN_API_KEY` is missing | Add the key to the job secrets |
| Every call raises a budget refusal | The pre-prod cap is too tight for the load | Raise the cap on the pre-prod workflow |
| Every call raises a rate-limit refusal | The rate limit is below the load rate | Raise the rate limit on the pre-prod workflow |
| The health check fails to connect | `NULLRUN_API_URL` is wrong | Point it at the pre-prod gateway |
| The capabilities probe reports a missing flag | The gateway is older than the SDK expects | Upgrade the gateway before the deploy |

### See also

- [Troubleshooting](#91-troubleshooting) — how to read SDK logs
- [Configuration → env vars](#15-configuration)
- [HTTP API → Capabilities](#73-http-api)


# 7. Reference


## 7.1 SDK API

The Python SDK lives in
[`nullrunio/nullrun-sdk-python`](https://github.com/nullrunio/nullrun-sdk-python).
Package name on PyPI: **`nullrun`**.

```bash title="shell"
pip install nullrun                    # core — covers every LLM SDK that uses httpx
pip install nullrun[opentelemetry]     # OTel span/metric export on top of the core
pip install nullrun[dev]               # pytest + respx + mypy + ruff + coverage
```

Auto-instrumentation for httpx-based libraries (`openai`,
`anthropic`, `openai-agents`, …) attaches lazily on the first
`@protect` call — see [Auto-instrumentation](#13-installation).

### Package surface

`dir(nullrun)` returns **only the curated `__all__` list** — 46 names.
Everything else the SDK exposes is imported on first attribute access, so it
never shows up in `dir()` or in tab-completion until you touch it.

```python title="public_surface.py"
from nullrun import init, protect, workflow, span, agent, chain
```

#### Curated surface (`__all__`, shown by `dir(nullrun)`)

| Symbol | Kind | Purpose |
|---|---|---|
| `__version__` | value | SDK version string. |
| `init` | function | Create the runtime eagerly. |
| `protect` | decorator | Gate a function. The only entry point for enforcement. |
| `shutdown` | function | Close the runtime and drain buffered events. |
| `on_error` | function | Register a global error hook. |
| `guard` | context manager | Turn an SDK error into a clean process exit. |
| `format_user_message` | function | Render an exception as end-user-facing text. |
| `set_user_message` | function | Override the message for one `error_code`. |
| `NullRunError` | exception | Base class for every SDK exception. |
| `NullRunDecision` | exception | Marker for expected policy outcomes. |
| `NullRunInfrastructureError` | exception | Marker for system failures. |
| `NullRunDeniedError` | exception | Operator refused this specific call. |
| `NullRunBudgetError` | exception | Budget exhausted. |
| `NullRunBudgetRecheckFailedError` | exception | Budget moved between gate and execute. |
| `NullRunToolBlockedError` | exception | Tool is in the block list. |
| `NullRunChainError` | exception | Chain-scope check failed. |
| `NullRunConsumeOverbudgetError` | exception | Actual cost exceeded the reservation. |
| `NullRunWorkflowInactiveError` | exception | Workflow is inactive. |
| `WorkflowKilledInterrupt` | exception | Operator kill signal. |
| `NullRunWorkflowKilledError` | exception | Typed name for the kill signal. |
| `NullRunApprovalNotYetApprovedError` | exception | Approval still pending. |
| `NullRunApprovalResponseMissingError` | exception | No approval row for the call. |
| `NullRunApprovalDeniedError` | exception | Operator denied the approval. |
| `NullRunApprovalExpiredError` | exception | Approval expired. |
| `NullRunApprovalReplayRejectedError` | exception | Approval already consumed. |
| `NullRunApprovalDigestMismatchError` | exception | Action digest drifted. |
| `NullRunApprovalToolDigestMismatchError` | exception | Tool digest drifted. |
| `NullRunApprovalToolMismatchError` | exception | Tool outside the approved set. |
| `NullRunApprovalDbUnavailableError` | exception | Approval store unreachable. |
| `NullRunMcpDestructiveBlockedError` | exception | Destructive MCP tool blocked. |
| `NullRunMcpReadonlyBypassBlockedError` | exception | Read-only MCP tool blocked. |
| `NullRunMcpApprovalRequiredError` | exception | MCP tool needs operator approval. |
| `NullRunProtocolError` | exception | Wire-protocol version mismatch. |
| `NullRunMalformedGateResponseError` | exception | Gate response is not a decision. |
| `NullRunGateIndeterminateError` | exception | Decision could not be determined. |
| `NullRunUnknownActionError` | exception | Control-plane action type unknown. |
| `NullRunUnclassifiedRefusalError` | exception | Refusal category not understood. |
| `NullRunTransportError` | exception | Transport failure. |
| `NullRunBackendError` | exception | Gateway returned 5xx. |
| `NullRunExecutionNotFoundError` | exception | Execution id unknown or expired. |
| `RateLimitError` | exception | Gateway returned 429. |
| `NullRunRateLimitRedisError` | exception | Rate limiter unavailable. |
| `NullRunAuthError` | exception | API key rejected. |
| `NullRunConfigError` | exception | Misconfiguration. |
| `BreakerTransportError` | exception | Events could not be delivered. |
| `InsecureTransportError` | exception | HTTPS required. |

#### Lazy surface

These names import fine (`from nullrun import X`) but stay out of `dir(nullrun)`.

| Group | Names |
|---|---|
| Runtime | `NullRunRuntime`, `get_runtime`, `get_protected_runtime`, `reset` |
| Context managers | `workflow`, `span`, `agent`, `chain` |
| Context getters | `get_workflow_id`, `get_trace_id`, `get_span_id`, `get_agent_id`, `get_call_model`, `get_call_tools`, `get_chain_id`, `get_chain_op` |
| Context setters | `set_call_context`, `set_chain_id`, `set_chain_op` |
| Tracing | `SpanContext`, `get_current_span`, `create_root_span`, `create_child_span`, `set_span`, `reset_span` |
| Actions | `ActionHandler`, `ActionType`, `ActionEvent`, `WebhookConfig`, `handle_action`, `register_action_handler`, `get_action_handler` |
| Exceptions | `BreakerError`, `NullRunBlockedException`, `NullRunAuthenticationError`, `WorkflowPausedException`, `TransportErrorSource` |
| Status | `NullRunStatus`, `RecentError`, `WorkflowState`, `ErrorContext` |
| Audit | `AuditEntry`, `AuditLogMeta`, `AuditLogPage`, `AuditQuery`, `AuditVerifyResult`, `AuditExportJob`, `AuditExportStatus` |
| Messages | `get_user_message` |

`TransportErrorSource` names where a transport failure came from:
`NETWORK_ERROR`, `GATEWAY_ERROR`, `AUTH_ERROR` and `BREAKER_OPEN`. The SDK
raises the first three. An open circuit breaker raises `BreakerTransportError`
instead.

### Lifecycle

#### `init`

```python title="init.py"
import nullrun

nullrun.init(api_key="nr_live_...", api_url="https://api.nullrun.io")
```

| Parameter | Default | Behaviour |
|---|---|---|
| `api_key` | `NULLRUN_API_KEY` | Required. A whitespace-only value is rejected. A missing key raises `NullRunAuthenticationError` with `error_code="NR-C001"`. |
| `api_url` | `NULLRUN_API_URL`, else `https://api.nullrun.io` | Gateway base URL. |
| `debug` | `False` | Turns on debug logging. |
| `fail_on_exit` | `False` | On a missing key, print the developer report to stderr and `sys.exit(1)` instead of raising. |
| `on_denied` | `"raise"` | `"raise"` or `"message"`. `"message"` makes the operator's refusal surface as `NullRunDeniedError`, whose `agent_message` is text the gateway marks safe to show a model. Any other value raises `ValueError`. The flag applies to a `denied` refusal only. |

`init()` is optional. The first `@protect` call creates the runtime lazily from
`NULLRUN_API_KEY`.

`init()` also registers `nullrun.shutdown()` with `atexit`, probes
`/api/v1/capabilities` for the protocol version, and installs
auto-instrumentation.

#### `protect`

```python title="protect.py"
import nullrun

@nullrun.protect
def send_email(to: str, body: str) -> None:
    ...
```

`protect(fn=None)` takes no keyword arguments. Both forms work:

```python
import nullrun

@nullrun.protect
def call(): ...

@nullrun.protect()
def call(): ...
```

It works on sync and async functions. Every protected call routes through the
gateway, which answers with one of five decisions: `allow`, `block`,
`require_approval`, `soft_pass`, or `deny`.

#### `shutdown`

```python title="shutdown.py"
nullrun.shutdown(timeout=2.0, flush=True)
```

`timeout` is reserved and unused today. `flush=False` skips the final network
call and cancels the flush thread. The call is safe and idempotent, and it is a
no-op when `init()` never ran.

#### `on_error`

```python title="on_error.py"
import nullrun

def report(err, ctx):
    print(err.error_code, ctx.stage)

unregister = nullrun.on_error(report)
```

The hook takes `(NullRunError, ErrorContext)` and must be synchronous. It runs
first, then the exception propagates. Hook exceptions are caught and logged at
debug level, so a misbehaving hook cannot break the SDK. The returned callable
unregisters the hook and is idempotent.

#### `guard`

```python title="guard.py"
import nullrun

with nullrun.guard(exit_code=1):
    run_my_agent("hello")
```

`guard(*, exit_code=1)` is a context manager. It catches every `NullRunError`
raised inside the block, prints a structured developer report to stderr, and
calls `sys.exit(exit_code)`. The kill signal propagates unchanged so it reaches
the top of the agent loop.

#### Messages

```python title="messages.py"
import nullrun

text = nullrun.format_user_message(exc)
nullrun.set_user_message("NR-B004", "You've used all your support credits.")
raw = nullrun.get_user_message("NR-B004")
```

`format_user_message(exc)` renders an exception as end-user-facing text. Use it
in place of `str(exc)` whenever a person reads the message — `str(exc)` carries
internal identifiers.

`set_user_message(code, text)` overrides the message for one `error_code` for
the lifetime of the process. Pass `text=""` to clear the override.
`get_user_message(code)` returns the override when one is set, the catalog
default otherwise.

### Context managers

| Manager | Yields | Behaviour |
|---|---|---|
| `workflow(name=None)` | `workflow_id` | Sets the workflow id for every event inside the block. The id is `name` or a fresh UUID. Also mints a root trace and span. |
| `span(name=None)` | `span_id` | Sets the active span for nested traces. |
| `agent(name=None)` | `agent_id` | Sets the agent identity for events inside the block. |
| `chain(chain_id, op="start")` | `chain_id` | Scopes the calls to one chain. `op` must be `"start"`, `"continue"`, `"end"`, or `"auto"`; any other value raises `ValueError`. `chain_id` must be a **UUID version 4**; another UUID version raises `ValueError` too. |

```python title="chain.py"
import uuid
import nullrun

chain_id = str(uuid.uuid4())
with nullrun.chain(chain_id, op="start") as cid:
    agent.run_long_loop()
```

`chain()` does not close the chain on exit. Close it explicitly with
`runtime.chain_end(chain_id)`.

#### `set_call_context`

```python title="set_call_context.py"
import nullrun

nullrun.set_call_context(
    model="claude-sonnet-4-6",
    tools=["search", "send_email"],
    max_output_tokens=4096,
)
```

`set_call_context(model=None, tools=None, max_output_tokens=None)` attaches
per-call context that the gateway uses when it evaluates the call. Pass `None`
to leave a field unchanged. `max_output_tokens` is sent only when it is a
positive integer.

Manual setters `set_chain_id(chain_id)` and `set_chain_op(op)` set the chain
scope directly. Each returns a token.

### Manual tracking

Tracking methods live on the runtime, not on the package. Reach the runtime
with `nullrun.get_runtime()`.

| Method | Signature |
|---|---|
| `track_llm` | `track_llm(input_tokens, output_tokens=0, *, model=None, latency_ms=None, metadata=None)` |
| `track_tool` | `track_tool(tool_name, duration_ms=None, *, is_retry=False, metadata=None)` |
| `track` | `track(event: dict)` |
| `track_event` | `track_event(event_type, **kwargs)` |

```python title="track_llm.py"
import nullrun

runtime = nullrun.get_runtime()
runtime.track_llm(
    input_tokens=response.usage.prompt_tokens,
    output_tokens=response.usage.completion_tokens,
    model="custom-model-v1",
    latency_ms=response.elapsed_ms,
)
```

```python title="track_tool.py"
import nullrun

nullrun.get_runtime().track_tool(
    tool_name="send_email",
    duration_ms=240,
    is_retry=False,
)
```

```python title="track.py"
import nullrun

nullrun.get_runtime().track({
    "type": "agent.milestone",
    "step": "research_complete",
    "elapsed_secs": 42,
})
```

```python title="track_event.py"
import nullrun

nullrun.get_runtime().track_event("workflow_start", workflow_id="wf-123")
```

`track_llm` reports token counts. The gateway computes cost from the tokens and
the org's pricing. A call the SDK cannot see is never billed, and the next
budget check can reject against a stale spend.

`track_tool` reports a tool call by name. The name reaches the policy engine,
so a blocked-tool policy can catch a manual call.

`track` takes an arbitrary event payload. The `type` field becomes the
filterable event category. `track_event` is the same thing with the event type
as its first argument.

### Runtime methods

| Method | Purpose |
|---|---|
| `status()` | Snapshot of the runtime. |
| `check_workflow_budget(*, model=None, estimated_tokens=None, max_output_tokens=None)` | Ask whether the workflow has budget left. |
| `execute(tool_name, input_data, mode="auto", ...)` | Run one tool call through the gateway. |
| `heartbeat(chain_id)` | Post a cadence heartbeat for a chain. |
| `ping_chain(chain_id, interval=30.0)` | Keep a chain alive on a timer. The interval must be between 10 and 120 seconds. |
| `cancel_execution(execution_id, reason=None)` | Cancel an in-flight execution. |
| `consume_approval(...)` | Close an approved grant. |
| `chain_end(chain_id)` | Close a chain. |
| `approximate_budget()` | Best-effort budget view for display. |
| `audit` | Audit log reader: `.list()`, `.verify()`, `.list_exports()`, `.create_export()`, `.export_status()`. |
| `shutdown(flush=True)` | Close the runtime. |

#### `status()`

```python title="status.py"
import nullrun

snapshot = nullrun.get_runtime().status()
print(snapshot.state)
```

`status()` returns a frozen `NullRunStatus` dataclass. It is safe to call from
any thread.

| Field | Meaning |
|---|---|
| `state` | `ok`, `degraded`, `offline`, or `misconfigured`. |
| `api_key_valid` | `True`, `False`, or `None` when never tested. |
| `api_key_prefix` | A fingerprint of the API key. Carries no character of the key. |
| `organization_id` | The org the key belongs to. |
| `workflow_id` | The bound workflow, or `None`. |
| `api_url` | The gateway base URL. |
| `backend_reachable` | `True`, `False`, or `None` when never tested. |
| `ws_connected` | `True`, `False`, or `None` when not started. |
| `workflow_state` | The remote workflow state, or `None`. |
| `recent_errors` | Bounded list of recent errors. |

There is no top-level `nullrun.status()`.

### Exceptions

Every public SDK exception inherits from `NullRunError` and carries four
structured fields: `error_code` (machine-readable, e.g. `"NR-B004"`),
`user_action` (imperative hint), `retryable` (bool), and `docs_url`.

`NullRunDecision` and `NullRunInfrastructureError` are marker classes. They let
host code catch every expected policy outcome with one clause, and every system
failure with another.

`NullRunBlockedException` carries `.workflow_id`, `.reason`, `.action`,
`.tool_name`, `.status_code`, and `.details`. It has **no** `.message`
attribute — use `str(exc)`.

The class tree, the `error_code` on each class, and the wire code each class
maps to live in one place: [Errors → SDK exception hierarchy](#75-error-codes).
The `error_code` catalog is in
[Errors → NR-* error code catalog](#75-error-codes).

### Catch-all pattern

```python title="catch_all_pattern.py"
import time

import nullrun
from nullrun import WorkflowKilledInterrupt, protect
from nullrun.breaker.exceptions import (
    NullRunBlockedException,
    RateLimitError,
    WorkflowPausedException,
)

try:
    step()
except WorkflowKilledInterrupt:
    raise                    # always re-raise — the kill must reach the top
except NullRunBlockedException:
    ...                      # budget, tool block, approval, chain
except RateLimitError as exc:
    time.sleep(exc.retry_after)
except WorkflowPausedException:
    ...                      # resume the workflow, then retry
```

`init()` is optional here. The first `protect`-decorated call creates the
runtime lazily from `NULLRUN_API_KEY`.

For global observability, register `nullrun.on_error(...)` instead of wrapping
every call site.

### User-facing messages

`nullrun.format_user_message(exc)` renders a `NullRunError` — or any object with
an `error_code` attribute — as end-user-facing text.

```python title="format_user_message.py"
import nullrun
from nullrun import NullRunBudgetError

@nullrun.protect
def chatbot(message: str) -> str:
    return agent.run(message)

try:
    reply = chatbot(message)
except NullRunBudgetError as exc:
    return nullrun.format_user_message(exc)
```

The catalog of default messages belongs to NullRun, so every deployment shows
the same wording for a given `error_code`. A deployment can override one code
with `set_user_message`. Overrides live in a per-process dict. They are not
persisted and not sent to the gateway.

An object without `error_code` gets a generic fallback. The function never
raises and never returns an empty string.

### See also

- [Decorators & context managers](#72-decorators-context-managers) — `@protect` and the
  extractor wrappers
- [Errors](#75-error-codes)
- [Errors → Decision vs. infrastructure](#75-error-codes)
- [Use with FastAPI](#64-use-with-fastapi)
- [Manual cost / event tracking](#610-manual-cost-event-tracking)
- [Auto-instrumentation](#13-installation)
- [Control plane](#44-control-plane-websocket)


## 7.2 Decorators & context managers

This page explains the contract each SDK symbol establishes with the
gate. The symbol table lives in [SDK API](#71-sdk-api).

`@protect` is the gate. Every protected call is evaluated against
tool patterns, budgets, rate limits, and approval policies before the
function body runs.

### The one decorator

`@protect` is the only public decorator in the SDK. It takes no
arguments.

```python title="protect_basic.py"
import nullrun

@nullrun.protect
def my_agent(prompt: str) -> str:
    return call_llm(prompt)

@nullrun.protect
async def my_async_agent(prompt: str) -> str:
    return await call_llm_async(prompt)

@nullrun.protect()      # also valid
def f(): ...
```

The SDK collects the facts — function name, arguments, keywords — and
ships them on the wire. The gateway decides. Business meaning ("this
moves money", "this needs a human") lives in control center policies, not
in a second decorator. See [Human
approval](#32-human-approval).

#### What happens on every call

| # | Step | What it does |
|---|---|---|
| 1 | Control-plane check | Applies a pending **kill** or **pause** before anything else. |
| 2 | Budget pre-flight | Reserves budget for the call. A refusal here stops the call. |
| 3 | Span start | Opens a span for the call. Never blocks. |
| 4 | Tool policy | Evaluates the tool against the org's policies. A refusal here stops the call. |
| 5 | Function body | Runs only if every step above allowed the call. |
| 6 | Tool track | Records the call and its cost. |

Argument names that look like credentials are replaced with `***`
before the call leaves your process. The name must match exactly:
`password`, `token`, `api_key`, `authorization`, `cookie`,
`credit_card_number`, `cvv`, `pin`, `otp`, `email`, `phone`, `ssn` and
similar. A name that only contains one of those words is not masked —
`card_number` and `user_password` keep their value. Credential-shaped
values are covered too, even under an argument name nobody listed: a
NullRun key, a JSON web token, an AWS access key id, an `sk-` secret, a
PEM private key, and a bearer credential are all replaced.

#### When the gateway cannot be reached

The SDK distinguishes four outcomes, and they are not the same thing:

| Outcome | What the SDK does |
|---|---|
| The gateway **refused** the call | The refusal is honoured. The call does not run. |
| The gateway is **unreachable** during the budget pre-flight (network error, timeout, 5xx) | The pre-flight is skipped and the call proceeds. |
| The gateway is **unreachable** during the tool policy check | The call does not run. The SDK raises `NullRunBlockedException`. |
| The answer **arrived but the SDK cannot read it** | The SDK raises `NullRunMalformedGateResponseError` (`NR-P002`). The call does not run. |
| The SDK's own code **faults** while it asks the gate | The SDK raises `NullRunGateIndeterminateError` (`NR-P004`). The call does not run. |

An unanswered question is not a yes. Only the budget pre-flight fails
open, and only on a transport error. The tool policy check fails
closed. A credential failure or an unreadable body raises instead of
proceeding.

`NULLRUN_SENSITIVE_FAIL_OPEN=1` exists for local development. On its
own it opens nothing: the set of tools allowed to fail open is empty
until you name the tools explicitly.

```python title="fail_open_tools.py"
import nullrun

runtime = nullrun.get_runtime()
runtime.register_fail_open_tools(["charge_card"])   # local development only
```

#### Sync and async differ in one place

A **kill** arriving mid-call is reported differently by the two
wrappers:

| Wrapper | The kill arrives as | The `on_error` hook fires |
|---|---|---|
| sync `@protect` | `NullRunBlockedException` with code `NR-W002` | yes |
| async `@protect` | `WorkflowKilledInterrupt` (code `NR-W002`) | no |

The sync form re-wraps the interrupt as a `NullRunBlockedException` and
fires the `on_error` hook. The async form lets the raw
`WorkflowKilledInterrupt` through and does not fire the hook.

Catch the kill by name, ahead of the decision branch:

```python title="catch_kill.py"
from nullrun import NullRunDecision, WorkflowKilledInterrupt

try:
    result = run_agent(prompt)
except WorkflowKilledInterrupt:
    raise          # a kill must reach the top of the loop
except NullRunDecision as decision:
    ...
```

#### Spans nest automatically

A protected call inside another protected call becomes a child span.
You do not thread span context through arguments.

```python title="protect_span_tree.py"
import nullrun
from nullrun import get_current_span

@nullrun.protect
def orchestrator(q):
    return researcher(q)             # child span

@nullrun.protect
def researcher(q):
    return get_current_span()        # its parent is the orchestrator span
```

### `with nullrun.guard():` — friendly exit

`guard()` turns any `NullRunError` raised inside the block into a
clean message on stderr and a non-zero exit.

```python title="guard_canonical.py"
import nullrun
from nullrun import protect

@protect
def my_agent(prompt: str) -> str:
    return call_llm(prompt)


if __name__ == "__main__":
    with nullrun.guard():
        print(my_agent("hello"))
```

`guard()` accepts one keyword: `exit_code` (default `1`).

The message is the user-facing sentence first, then the developer
detail — the error code, where it happened, why, and how to fix it.
See [Error handling](#43-error-handling) for the full
report shape.

These propagate unchanged:

- `WorkflowKilledInterrupt` — the kill must reach the top of the loop.
- `KeyboardInterrupt` and `SystemExit`.
- Any exception that is not a `NullRunError` — your own bugs deserve
  an honest traceback.

Use `guard()` at the entry point of a script or CLI. In a library or
a long-running service, catch `NullRunError` instead — `guard()`
exits the process.

### Context managers

| Context manager | Parameters | What it sets |
|---|---|---|
| `with workflow(name=None)` | `name: str \| None` | The workflow scope. Everything inside is attributed to this workflow. |
| `with span(name=None)` | `name: str \| None` | A child span of the active parent. |
| `with agent(name=None)` | `name: str \| None` | The agent identity, for per-agent cost attribution. |
| `with chain(chain_id, op="start")` | `chain_id: str` (UUID v4), `op: str` | A chain — a group of calls that run as one unit under a shared budget. |

#### `workflow()` and the policy binding

The workflow name is what links a run to the budget and policies you
configured in the control center. Give it the same name as the workflow
your API key is bound to. If you leave it unset, the SDK generates one
and the run carries no workflow policies.

#### `chain()` and the UUID v4 requirement

```python title="chain_uuid.py"
import uuid
import nullrun

chain_id = str(uuid.uuid4())       # must be a UUID v4 string
with nullrun.chain(chain_id, op="start"):
    my_long_running_agent()
```

`op` is one of `start`, `continue`, `end`, `auto`. The default is
`start`.

The `chain_id` is validated when you enter the block. A malformed id
raises `ValueError`. Use `uuid.uuid4()` rather than a readable slug —
the SDK cannot tell a typo from a deliberate identifier.

A chain is the companion to a hard budget: a bounded overrun is
allowed only while a chain is active. Long-running streams should also
call `runtime.ping_chain(chain_id, interval=30.0)` so the chain stays
alive between calls.

#### Nested spans

```python title="nested_span.py"
import nullrun

with nullrun.workflow("my-agent"):
    with nullrun.span("plan-generation"):
        plan = my_agent(user_input)
        with nullrun.span("tool-call"):
            tool.invoke(plan)
```

### `set_call_context()` — per-call data for the gate

```python title="set_call_context.py"
import nullrun

nullrun.set_call_context(
    model="claude-sonnet-4-6",
    tools=["send_email", "refund_customer"],
)
```

| Parameter | Type | Default | Effect when unset |
|---|---|---|---|
| `model` | `str \| None` | `None` | The gateway uses the workflow's default model rate. |
| `tools` | `list[str] \| tuple[str, ...] \| None` | `None` | The gateway evaluates the tool block against the protected function's own name only. |
| `max_output_tokens` | `int \| None` | `None` | The gateway uses its default output estimate. |

Call it inside a `with workflow(...)` block, before the protected
call. The gateway uses the model to price the reservation, and the
tool list to evaluate the tool block against the tools the call
actually intends to use.

`None` leaves the previous value unchanged. Pass `[]` to clear the
tool list.

### Approval rules and the action digest

Every protected call ships the function name, its arguments, and a
SHA-256 digest of the call's business impact. An approval rule that
inspects argument values names the parameter it cares about. The
gateway reads the live value from the request — there is nothing to
configure on the SDK side.

The digest binds the approval to the exact payload. If the amount or
the arguments change between the approval and the execution, the
gateway refuses.

### When to use what

| Task | API |
|---|---|
| Guard a function that calls an LLM or a tool | `@nullrun.protect` |
| Attribute a run to a workflow | `with nullrun.workflow("name"):` |
| Price the call and match the tool block against a tool list | `nullrun.set_call_context(model=..., tools=[...])` |
| Run a bounded overrun under a shared budget | `with nullrun.chain(uuid.uuid4(), op="start"):` |
| Nest a step in the trace | `with nullrun.span("name"):` |
| Attribute cost to one agent | `with nullrun.agent("name"):` |
| Fail fast on a bad config | `nullrun.init(fail_on_exit=True)` |
| Friendly exit at the entry point | `with nullrun.guard():` |
| Send every SDK error to your logging | `nullrun.on_error(handler)` |
| Track an LLM call the instrumentation cannot see | `nullrun.get_runtime().track_llm(...)` |
| Track a tool call the instrumentation cannot see | `nullrun.get_runtime().track_tool(...)` |
| Read the runtime state | `nullrun.get_runtime().status()` |

### Anti-patterns

!!! warning "Don't put `with nullrun.guard():` inside a protected body"
    The guard only catches errors raised inside its own block. A gate
    refusal is raised by the wrapper before the body runs, so it never
    reaches the block. The process exits with a raw traceback instead
    of the clean report.

!!! warning "Don't pass a cost to `track_llm`"
    Cost is recomputed on the gateway from the real token counts. The
    SDK sends tokens, not money.

!!! warning "Don't invent a `chain_id`"
    A `chain_id` must be a UUID v4. A readable slug raises
    `ValueError`.

!!! danger "Don't set `model` to lower the cost"
    `model` only selects which rate the gateway prices the
    reservation with. The charge comes from the real token counts, so a
    lower projected cost does not lower the bill.

### See also

- [SDK API](#71-sdk-api) — the symbol table and manual tracking
- [Errors](#75-error-codes) — the exception hierarchy and the error-code catalog
- [Human approval](#32-human-approval) — typed predicates and the action digest
- [Workflow context](#41-workflow-context) — chains, soft mode, and the workflow scope
- [Custom tracking](#610-manual-cost-event-tracking) — when to track by hand


## 7.3 HTTP API

Base URL: `https://api.nullrun.io`.

REST paths start with `/api/v1`. The WebSocket control plane path does not.

Every response body is JSON.

### Protocol header

Every request to a gateway endpoint carries the wire-protocol version:

```http title="HTTP"
X-NULLRUN-PROTOCOL: 4
```

The value is a bare integer. The gateway accepts 2 to 11, and its current
version is 11. The SDK sends 4 on every call, so you never set the header by
hand. A missing or unsupported version answers `400`.

### Authentication

Two schemes. They are not interchangeable.

| Caller | Headers | Credential |
|---|---|---|
| SDK | `X-API-Key` | The API key, for example `nr_live_...` |
| SDK with request signing | `X-API-Key`, `X-Signature`, `X-Signature-Timestamp` | The API key plus the signing secret |
| Control center | `Authorization: Bearer <session_token>` | A session token from `POST /api/v1/auth/login` |

The enforcement path reads `X-API-Key`. It does not read
`Authorization: Bearer`, so a call that carries only the bearer token answers
`401` with `API_KEY_MISSING`. The SDK sends both headers.

The signing secret is separate from the API key. It arrives in the
`POST /api/v1/auth/verify` response as `secret_key`.

The signature is the hex-encoded HMAC-SHA256 of this string, keyed with the
signing secret:

```text title="Signature"
<timestamp>:<api_key>:<sha256_hex_of_the_request_body>
```

`X-Signature-Timestamp` carries the Unix epoch seconds used in the signature.
The gateway rejects a stale timestamp with `401`.

The SDK computes the signature for every request on its own. A request body is
signed as the exact bytes that go on the wire. The gateway requires a valid
signature on the four enforcement calls: `POST /api/v1/gate`,
`POST /api/v1/execute`, `POST /api/v1/track`, and `POST /api/v1/track/batch`.
No other route reads the `X-Signature` header. Other routes authenticate their
own way — the payment and chat webhooks verify a provider signature.

The requirement is controlled by `NULLRUN_HMAC_REQUIRED`. The hosted
deployment turns it on. When it is off, the gateway logs one warning and stops
verifying signatures.

### SDK endpoints

These are the endpoints the SDK calls. You do not normally call them by hand.

| Method | Path | What it does |
|---|---|---|
| `POST` | `/api/v1/auth/verify` | Verifies the API key. Returns the credential bundle: `organization_id`, `workflow_id`, `secret_key`, `key_version`, plan, features, limits. |
| `GET` | `/api/v1/capabilities` | Reports the supported wire-protocol range, the feature flags, and the endpoint paths. |
| `POST` | `/api/v1/gate` | Checks the budget for one action and reserves it. Returns the decision and a server-minted `execution_id`. Sending `chain_op: "end"` closes a chain. |
| `POST` | `/api/v1/execute` | Evaluates the policy for one tool call. This is the primary enforcement point. |
| `POST` | `/api/v1/track` | Commits one spend event against a reservation. |
| `POST` | `/api/v1/track/batch` | Commits up to 100 spend events in one request. |
| `POST` | `/api/v1/approvals/{approval_id}/consume` | Closes an approved grant without running the tool. Idempotent. |
| `POST` | `/api/v1/heartbeat` | Reports that a long-running workflow is still alive. The body carries `chain_id`. |
| `POST` | `/api/v1/cancel` | Cancels an in-flight execution. Idempotent. |
| `GET` | `/api/v1/status/{workflow_id}` | Reads the state of one workflow. The SDK polls this when the WebSocket is unavailable. |
| `GET` | `/api/v1/budget/approximate` | Returns the approximate budget view. |
| `GET` | `/api/v1/orgs/{org_id}/audit-log` | Lists audit entries. |
| `GET` | `/api/v1/orgs/{org_id}/audit-log/verify` | Verifies the audit trail. |
| `GET`, `POST` | `/api/v1/orgs/{org_id}/audit-log/export` | `GET` lists the ten most recent export jobs. `POST` enqueues an export job and returns a job id. |
| `GET` | `/api/v1/orgs/{org_id}/audit-log/export/{job_id}/status` | Reports the export job status. |
| `WS` | `/ws/control/{organization_id}` | Streams control-plane events: kill, pause, approval decisions, key rotation. |

`POST /api/v1/check` is not served. It answers `410` and names
`POST /api/v1/gate` as the path to use.

#### The credential bundle

`POST /api/v1/auth/verify` answers with the fields the SDK needs to run.

| Field | Type | Notes |
|---|---|---|
| `organization_id` | string | The org the key belongs to. Required — a response without it is an error. |
| `organization_name` | string \| null | The org display name. |
| `plan` | string | The plan tier. |
| `features` | object | The plan's feature flags. |
| `limits` | object | The plan's limits. |
| `role` | string \| null | The member role. `null` on the API-key path. |
| `workflow_id` | string \| null | The workflow the key is bound to. `null` on an unbound key. |
| `secret_key` | string \| null | The signing secret. `null` when the key does not sign. |
| `key_version` | number \| null | The active signing-secret version. A change means the secret rotated. |

### The gate call

`POST /api/v1/gate` is the budget step of the enforcement path. It checks
the budget for one action, reserves the money, and answers with a decision.
The tool policy is evaluated at `POST /api/v1/execute`, which the SDK calls
right after.

#### Request

| Field | Required | Notes |
|---|---|---|
| `organization_id` | yes | The org the call runs for. |
| `execution_id` | yes | The execution this call belongs to. |
| `trace_id` | yes | The trace this call belongs to. |
| `mode` | yes | `auto`, `inline`, or `strict`. The SDK sends `auto` and never sends `inline`. |
| `tool` | no | One tool name. The gate reads `tool` or `tools`, never `tool_name`. |
| `tools` | no | A list of tool names the caller intends to use. |
| `model` | no | The model the call will use, for an LLM check. |
| `estimated_tokens` | no | The input-token estimate, for an LLM check. |
| `max_output_tokens` | no | The caller's own output-token ceiling. |
| `check_type` | no | `llm` or `tool`. |
| `workflow_id` | no | The workflow the call runs for. |
| `chain_id` | no | The chain the call belongs to. |
| `chain_op` | no | `start`, `continue`, or `end`. |
| `approval_id` | no | The approval presented on the post-approval re-check. |
| `business_impact` | no | The value the call moves. Omit it when there is none. |
| `action_digest` | no | Digest of the business impact, re-sent on the re-check. |
| `tool_class` | no | `builtin`, `mcp`, `custom`, or `invalid`. |
| `tool_arguments` | no | The tool-call arguments, as a JSON object. An approval rule that matches on arguments reads this bag. |
| `tool_params` | no | The older name for the same bag. The gate reads `tool_arguments` first. |
| `parent_execution_id` | no | The execution that spawned this one. |

`business_impact` has two kinds. There is no `none` kind — omit the field
instead.

| `kind` | Fields |
|---|---|
| `money` | `direction` (`outflow` or `inflow`), `amount_minor` in cents, `currency`. |
| `tool_call` | `tool_name`, `params`. |

#### Decision values

| Decision | Meaning |
|---|---|
| `allow` | The call may run. |
| `block` | The call may not run. |
| `require_approval` | The call may run after an operator approves it. The answer carries an `approval_id`. |
| `soft_pass` | The call runs, and the event is recorded for review. |
| `deny` | The call may not run, and the model may adapt and try something else. |

#### Response

| Field | Notes |
|---|---|
| `decision` | One of the five values above. |
| `decision_source` | Which rule produced the decision. |
| `explanation` | The reason, in human text. |
| `execution_id` | The server-minted id for this execution. |
| `operation_id` | An echo of the `operation_id` you sent. The SDK keeps its own value and falls back to this one. The field is absent on some refusal responses. |
| `approval_id` | The approval to wait on. Present on `require_approval`. |
| `remaining_budget_cents` | The budget left in the period, in cents. |
| `projected_cost_cents` | The reserved cost, in cents. |
| `retry_after_ms` | How long to wait, in milliseconds. |
| `action_digest` | The digest the gateway recorded for the approval. |
| `category` | `denied`, `budget`, `halt`, or `infra`. |
| `budget_enforcement` | `enforced`, `not_configured`, or `unknown`. |
| `user_message` | Text to show the user. |
| `agent_message` | Text to show the model. |

#### Money units

Three units appear on the wire. They are not interchangeable.

| Unit | Where it appears |
|---|---|
| Cents, integer | The request wire: `cost_cents`, `reserved_cost_cents`, `budget_cents`, `threshold_cents`, `amount_minor`, `threshold_minor`, `projected_cost_cents`, `remaining_budget_cents`. |
| Millicents, integer | The ledger and the lease responses: `cost_millicents`, `granted_millicents`, `spent_millicents`, `monthly_cost_millicents`. One millicent is 1/1000 of a cent. |
| US dollars, float | The track response: `total_cost_usd` and `rate_per_minute` on the snapshot, `cost_usd` on each tool-history entry. |

A field named `projected_cost_millicents` does not exist on the wire. The gate
reports `projected_cost_cents`.

### Idempotency

Two body fields carry the idempotency key. Each endpoint reads one of them.

| Field | Read by | Value |
|---|---|---|
| `operation_id` | `/api/v1/gate` | A UUID v4 minted by the SDK for one budget check. The gateway keys its duplicate-detection on this field and echoes it back in the response. `/api/v1/execute` accepts and echoes the field too, but does not deduplicate on it. |
| `idempotency_key` | `/api/v1/track`, `/api/v1/track/batch` | The SDK's own `operation_id`. The SDK stamps it on the track body, and adds the span id after a colon when the event belongs to a span. |

The gateway binds the reservation to the key, so a repeated call with the same
key settles the same action instead of charging twice. The SDK mints one
`operation_id` per budget check and carries it across the gate, the execute
and the track of that call.

The gate ignores `idempotency_key` if you send it. Use `operation_id` on the
gate.

Two endpoints are idempotent by contract and need no key from you:

- `POST /api/v1/cancel` — a second call on the same execution is a no-op.
- `POST /api/v1/approvals/{approval_id}/consume` — an already-consumed grant
  answers `200`.

### Control-plane endpoints

These endpoints drive the control center and the control plane. They are not part
of the SDK's request path.

#### Workflows

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/orgs/{org_id}/workflows` | Create a workflow. |
| `GET` | `/api/v1/orgs/{org_id}/workflows` | List workflows. |
| `GET` | `/api/v1/orgs/{org_id}/workflows/{workflow_id}` | Get one workflow. |
| `PATCH` | `/api/v1/orgs/{org_id}/workflows/{workflow_id}` | Update the budget, the name, and other settings. |
| `POST` | `/api/v1/orgs/{org_id}/workflows/{workflow_id}/pause` | Pause the workflow. |
| `POST` | `/api/v1/orgs/{org_id}/workflows/{workflow_id}/resume` | Resume the workflow. |
| `POST` | `/api/v1/orgs/{org_id}/workflows/{workflow_id}/kill` | Kill the workflow. |

The create body carries `name`, `external_id`, and an optional `budget_cents`.
The org-scope key is `external_id`: two workflows may share a `name`, and a
repeated `external_id` matches the existing workflow.

#### Policies

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/orgs/{org_id}/policies` | List policies. A single policy is not addressable by id — read it from the list. |
| `POST` | `/api/v1/orgs/{org_id}/policies` | Create a policy. |
| `PATCH` | `/api/v1/orgs/{org_id}/policies/{policy_id}` | Update a policy. |
| `DELETE` | `/api/v1/orgs/{org_id}/policies/{policy_id}` | Delete a policy. |
| `POST` | `/api/v1/orgs/{org_id}/policies/{policy_id}/toggle` | Switch a policy between active and inactive. |
| `GET` | `/api/v1/orgs/{org_id}/policies/templates` | List policy templates. |
| `POST` | `/api/v1/orgs/{org_id}/policies/templates/{template_id}/enable` | Enable a template. |
| `DELETE` | `/api/v1/orgs/{org_id}/policies/templates/{template_id}` | Disable a template. |

The most restrictive applicable policy wins. See
[Concepts → Policies](#22-policies).

A policy body carries:

| Field | Values |
|---|---|
| `name` | The policy name. |
| `policy_type` | `rate_limit`, `budget_limit`, or `tool_block`. |
| `scope` | `org` or `workflow`. |
| `workflow_id` | The workflow the policy applies to. Required when `scope` is `workflow`. |
| `config` | The policy payload. Required. The keys depend on `policy_type`. |
| `enforcement_mode` | `Hard` or `Soft`. Applies to `budget_limit` policies only. |
| `max_overdraft_cents` | Maximum overdraft in cents. Applies to `budget_limit` policies only. |
| `max_overdraft_percent` | Maximum overdraft as a percentage of the budget. Applies to `budget_limit` policies only. |
| `loop_threshold` | The loop-detection ceiling. |
| `loop_window_secs` | The loop-detection window, in seconds. |
| `anomaly_mode` | `lite`, `moderate`, or `strict`. |
| `mcp_destructive_policy` | `allow`, `block`, or `approval`. Applies to MCP tools that report themselves destructive. |
| `mcp_readonly_policy` | `allow`, `block`, or `approval`. Applies to MCP tools that report themselves read-only. |

| `policy_type` | `config` keys |
|---|---|
| `rate_limit` | `max_calls_per_minute`. Required. An integer. `0` means no limit. |
| `budget_limit` | `budget_cents`. A whole number of cents, greater than zero. `consume_epsilon_cents` sets the consume tolerance in cents. |
| `tool_block` | `tool_pattern` — a JSON array of glob patterns — plus `blocked_tools`, `tools`, and `parameter_conditions`. |

The gateway enforces the smallest `max_calls_per_minute` across the active
rate-limit policies that apply to the call.

`tool_pattern` holds an array of strings. A bare string is rejected with `422`.
The key is singular: the plural `tool_patterns` is also rejected with `422`.

#### Approvals

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/orgs/{org_id}/approvals` | List approvals. |
| `POST` | `/api/v1/orgs/{org_id}/approvals/{approval_id}/approve` | Approve a pending approval. An already-decided approval answers `409`. |
| `POST` | `/api/v1/orgs/{org_id}/approvals/{approval_id}/deny` | Deny a pending approval. |
| `GET` | `/api/v1/orgs/{org_id}/approvals/history` | List decided approvals. |

#### Executions, audit, and usage

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/orgs/{org_id}/executions` | List executions. |
| `GET` | `/api/v1/orgs/{org_id}/executions/{execution_id}` | Get one execution. |
| `GET` | `/api/v1/orgs/{org_id}/audit-log` | List audit entries. |
| `GET` | `/api/v1/orgs/{org_id}/audit-log/verify` | Verify the audit trail. |
| `GET` | `/api/v1/orgs/{org_id}/audit-log/export` | List the ten most recent export jobs. Each row carries `id`, `status`, `created_at`, `completed_at` and `record_count`. |
| `POST` | `/api/v1/orgs/{org_id}/audit-log/export` | Enqueue an export job and return a job id. |
| `GET` | `/api/v1/orgs/{org_id}/audit-log/export/{job_id}/status` | Poll the export job. |
| `GET` | `/api/v1/orgs/{org_id}/audit-log/export/{job_id}/download` | Download the exported file. |
| `GET` | `/api/v1/orgs/{org_id}/traces` | List trace spans. |
| `GET` | `/api/v1/orgs/{org_id}/traces/{trace_id}` | Get one trace with its full span tree. |
| `GET` | `/api/v1/orgs/{org_id}/incidents` | List active and recent incidents. |
| `GET` | `/api/v1/orgs/{org_id}/usage` | Usage breakdown. |
| `GET` | `/api/v1/orgs/{org_id}/quota` | Usage breakdown. Same payload as `/usage`. |
| `GET` | `/api/v1/orgs/{org_id}/dashboard` | Control center overview payload. |
| `GET` | `/api/v1/orgs/{org_id}/control-center` | Workflows, recent decisions, and alerts in one call. |

#### Budget and status

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/budget/approximate` | Approximate budget view for display. See [Budgets](#31-budgets). |
| `GET` | `/api/v1/orgs/{org_id}/status` | One call with the spend, the budget, the rate usage, the plan limits, and the plan. |

`GET /api/v1/budget/approximate` answers with the estimate and its
provenance.

| Field | Notes |
|---|---|
| `org_id` | The org the estimate belongs to. |
| `current_spend_cents_estimate` | The estimated spend. |
| `is_approximate` | Always `true`. The endpoint is advisory only. |
| `source` | Where the number came from. |
| `confidence` | How stale the number may be. |
| `last_updated_at` | ISO-8601 UTC of the read. |

The endpoint answers `503` when it cannot produce an estimate. The body
carries `error_code`, `error_message`, and `retry_after_ms`. Render a retry
prompt, not a zero spend.

`GET /api/v1/orgs/{org_id}/status` answers with the org's money and limits.

| Field | Notes |
|---|---|
| `usage_today_cents` | Spend over the last 24 hours. |
| `usage_month_cents` | Spend over the current billing period. |
| `budget_used_cents` | Org budget used in the period. |
| `budget_remaining_cents` | Budget left in the period. `null` together with `budget_limit_cents` and `budget_pct_used` when the plan sets no org cap. |
| `budget_limit_cents` | The plan's org cap, in cents. `null` under the same condition. |
| `budget_pct_used` | Percentage of the cap used. `null` under the same condition. |
| `time_to_limit` | Absent when no exhaustion is projected in the period. Otherwise an object with `seconds_remaining` and a `display` string. |
| `rate` | Rate-limit status for the org. |
| `per_key_rate` | Per-key rate visibility. Absent when not available. |
| `limits` | Plan limits and the current usage against them. |
| `plan`, `plan_name` | The plan tier and its display name. |
| `subscription_status` | `active` or `past_due`. |
| `cost_estimate_approximate` | Always `false`. The server prices the spend from its own catalog. |
| `cost_accuracy_hint` | A note that names the pricing source. |
| `period_window` | The period the month counters are read from. |

#### Organization

| Method | Path | Purpose |
|---|---|---|
| `GET`, `PATCH`, `DELETE` | `/api/v1/orgs/{org_id}` | Read, update, or delete the organization. |
| `GET` | `/api/v1/orgs/{org_id}/members` | List members. |
| `PATCH` | `/api/v1/orgs/{org_id}/members/{member_id}` | Change a member's role. |
| `DELETE` | `/api/v1/orgs/{org_id}/members/{member_id}` | Remove a member. |
| `GET` | `/api/v1/orgs/{org_id}/invites` | List invites. |
| `POST` | `/api/v1/orgs/{org_id}/invites` | Invite a member. |
| `DELETE` | `/api/v1/orgs/{org_id}/invites/{invite_id}` | Revoke an invite. |
| `POST` | `/api/v1/orgs/{org_id}/invites/{invite_id}/resend` | Resend the invite email. |
| `GET` | `/api/v1/invites/{token}` | Public invite details. |
| `POST` | `/api/v1/invites/{token}/accept` | Accept an invite. |
| `POST` | `/api/v1/invites/{token}/decline` | Decline an invite. |

#### API keys

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/orgs/{org_id}/api-keys` | List keys. |
| `POST` | `/api/v1/orgs/{org_id}/api-keys` | Mint a key. |
| `DELETE` | `/api/v1/orgs/{org_id}/api-keys/{key_id}` | Revoke a key. |
| `POST` | `/api/v1/orgs/{org_id}/api-keys/{key_id}/rotate` | Rotate the signing secret in place. |
| `GET` | `/api/v1/workflows/{workflow_id}/api-keys` | List the keys bound to one workflow. |

The raw key and the signing secret are returned once, at mint time. Store
them at once.

#### Alerts

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/orgs/{org_id}/alerts` | List active alerts. |
| `POST` | `/api/v1/orgs/{org_id}/alerts/{alert_id}/dismiss` | Dismiss one alert. |
| `POST` | `/api/v1/orgs/{org_id}/alerts/dismiss-all` | Dismiss every alert. |
| `GET`, `POST` | `/api/v1/orgs/{org_id}/alert-channels` | List or create alert channels. |
| `GET`, `PATCH` | `/api/v1/orgs/{org_id}/notification-settings` | Per-user notification settings. |

#### Auth

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/auth/register` | Create an account. Returns an API key and a signing secret. |
| `POST` | `/api/v1/auth/login` | Exchange email and password for a session token. |
| `POST` | `/api/v1/auth/verify` | Verify an API key and return the credential bundle. |
| `POST` | `/api/v1/auth/verify-email` | Confirm an email address. |
| `POST` | `/api/v1/auth/forgot-password` | Start a password reset. |
| `POST` | `/api/v1/auth/reset-password` | Finish a password reset. |
| `GET` | `/api/v1/auth/me` | The signed-in user. |
| `DELETE` | `/api/v1/auth/session` | Revoke the session. |

#### Health

The health endpoints sit on the gateway's top-level router. They are not
under `/api/v1`. They answer `200` when healthy and `503` otherwise, with a
body listing each dependency.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health/live` | Liveness — the process accepts connections. |
| `GET` | `/health/ready` | Readiness — the dependencies are reachable. |
| `GET` | `/health/startup` | Startup — `200` once migrations finish, `503` while booting. |
| `GET` | `/health` | Alias for `/health/live`. |
| `GET` | `/healthz` | Alias for `/health/live`. |

### Capabilities

`GET /api/v1/capabilities` reports the wire contract the gateway supports.

| Field | Type | Notes |
|---|---|---|
| `protocol_version` | number | The protocol version the gateway speaks. |
| `min_protocol_version` | number | The oldest protocol version the gateway accepts. |
| `max_protocol_version` | number | The newest protocol version the gateway accepts. |
| `capabilities` | object | The feature flags, nested under this key. |
| `endpoints` | object | The endpoint paths the gateway serves. |
| `server_version` | string | The gateway release tag. |
| `built_at` | string \| null | ISO-8601 build timestamp, when the build reports one. |

The SDK probes this endpoint during `init()` and logs a warning when the
backend is not v3-ready, or when the SDK's own version is below the minimum
the v3 wire contract needs. The probe is advisory: `init()` does not fail. A
protocol version outside the gateway's range is refused per request with
`400 PROTOCOL_TOO_OLD`.

### WebSocket control plane

`WS /ws/control/{organization_id}` streams control-plane events to a
connected SDK. The `{organization_id}` comes from the credential bundle, so the
SDK derives the URL on its own.

Server → client message types: `initial_state`, `state_change`,
`policy_invalidated`, `key_rotated`, `resync_required`, `error`, `pong`,
`approval_resolved`, `subscribed`.

Client → server message types: `ack`.

The SDK reads the workflow state from the socket. When the socket is
unavailable, the SDK falls back to polling `GET /api/v1/status/{workflow_id}`.

See [Control plane](#44-control-plane-websocket) for the reaction matrix.

### Example

The control center endpoints take a session token. The SDK endpoints take an API
key.

```bash title="shell"
TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
ORG_ID=8a3b1c7d-...

curl -X POST "https://api.nullrun.io/api/v1/orgs/$ORG_ID/workflows" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "production-bot",
    "external_id": "production-bot",
    "budget_cents": 5000
  }'
```

```bash title="shell"
curl "https://api.nullrun.io/api/v1/orgs/$ORG_ID/status" \
  -H "Authorization: Bearer $TOKEN"
```

### Errors

Every error response carries a machine-readable code. See
[Error codes](#75-error-codes) for the gateway slugs, the enforcement codes, and the
SDK exception hierarchy.

### See also

- [Error codes](#75-error-codes)
- [SDK API](#71-sdk-api)
- [Control plane](#44-control-plane-websocket)
- [Budgets](#31-budgets)


## 7.4 Error lookup

Every NullRun exception carries a `docs_url`. The SDK sets it to this page,
because one page holds the whole vocabulary and a per-code page for every
code would be a worse place to send a reader.

The reference itself lives in one place:
[Error codes → reference](#75-error-codes).

| You have | Go to |
|---|---|
| An `NR-*` code | [NR-* error code catalog](#75-error-codes) |
| A gateway wire code, such as `BUDGET_HARD_BLOCKED` | [Gateway wire error codes](#75-error-codes) |
| A Python exception class | [SDK exception hierarchy](#75-error-codes) |
| A generic API error with an `error` slug | [Generic API errors](#75-error-codes) |
| A failure you need to classify, not just name | [Decision vs. infrastructure](#75-error-codes) |

To branch in your own code, read `exc.error_code`. To show the user a message,
call `nullrun.format_user_message(exc)`. To decide whether to retry, read
`exc.retryable`.

See [Concepts → Error handling](#43-error-handling) for the
exception → hook → message flow, and [SDK API](#71-sdk-api) for the
fields each exception carries.


## 7.5 Error codes

The gateway's error-code registry is the source of truth for what the gateway
can refuse and what HTTP status it answers with. The SDK projects that registry
onto its own catalog: every SDK exception carries an `error_code` such as
`"NR-B004"`, and that value is the user-facing identifier to branch on.

Three vocabularies meet on the wire.

| Vocabulary | Where it appears | Shape |
|---|---|---|
| Gateway `error` slug | The `error` field of a generic API error | `snake_case`, e.g. `rate_limit_exceeded` |
| Gateway `error_code` | The `error_code` field of a gate refusal | `SCREAMING_SNAKE_CASE`, e.g. `BUDGET_HARD_BLOCKED` |
| SDK `error_code` | The `error_code` attribute of an SDK exception | `NR-*`, e.g. `NR-B004` |

A generic API error carries three fields: `error` (the slug), `message` (human
text), and `code` (a `SCREAMING_SNAKE_CASE` companion). Read `error` first.

A gate refusal carries `error_code` (the enforcement code), `error_message`,
and `details` (structured context). The SDK reads the code from the top level
or from inside `details`.

For the three-layer error model — structured exceptions → `on_error` hook →
`format_user_message` and `with nullrun.guard():` — see
[Concepts → Error handling](#43-error-handling).

### Generic API errors

A generic API error answers with a slug, a message, and a legacy code.

| `error` slug | HTTP | `code` | When |
|---|---|---|---|
| `bad_request` | 400 | `INVALID_INPUT` | Generic invalid input. |
| `invalid_json` | 400 | `INVALID_JSON` | The request body could not be parsed as JSON. |
| `bad_request` | 415 | `INVALID_INPUT` | The request body has no `application/json` content type. |
| `unauthorized` | 401 | `UNAUTHORIZED` | The key is missing, invalid, or expired. |
| `forbidden` | 403 | `FORBIDDEN` | Authenticated, but not allowed. |
| `not_found` | 404 | `NOT_FOUND` | The resource does not exist or is not visible to the caller. |
| `conflict` | 409 | `CONFLICT` | A duplicate, or a race the caller lost. |
| `conflict` | 409 | `APPROVAL_ALREADY_DECIDED` | The approval was already decided. |
| `conflict` | 409 | `APPROVAL_EXPIRED` | The approval expired. |
| `validation_error` | 422 | `VALIDATION_FAILED` | The body parsed but failed schema validation. |
| `validation_error` | 422 | `INVALID_FIELD` | A field in the body has the wrong shape. |
| `plan_limit_exceeded` | 422 | `PLAN_LIMIT_EXCEEDED` | A plan cap was hit. `details.resource` names the dimension. |
| `workflow_limit_reached` | 422 | `WORKFLOW_LIMIT_REACHED` | The active-workflow cap was hit. |
| `rate_limit_exceeded` | 429 | `RATE_LIMIT_EXCEEDED` | A rate cap was hit. The body carries `retry_after`. |
| `internal_error` | 500 | `INTERNAL_ERROR` | A server-side fault. |
| `internal_error` | 503 | `INTERNAL_ERROR` | A dependency was unavailable. The body carries `retry_after`. |
| `not_implemented` | 501 | `NOT_IMPLEMENTED` | The endpoint is not implemented. |

Plan caps all surface as `plan_limit_exceeded`. There is no slug per
dimension — read `details.resource`.

A generic API error becomes `NullRunBackendError` in the SDK, except on these
statuses: `401` and `403` raise `NullRunAuthenticationError`, and `429` raises
`RateLimitError`.

### Gateway wire error codes

A gate refusal carries one of the codes below in `error_code`. The `category`
says what the caller may do about it.

| Category | Meaning |
|---|---|
| `denied` | A rule judged this call unacceptable. Another call may pass, so the model may adapt and try something else. |
| `budget` | A money or quota boundary is exhausted. Stop. Do not retry and do not re-plan. |
| `halt` | The run is over. Retrying, adapting, and waiting all fail the same way. |
| `infra` | A system fault. Retry with backoff. |

Only a `denied` refusal is safe to turn into model-readable text. A model told
that its budget is exhausted will go looking for another tool.

The SDK maps a recognised code to a typed exception. An unrecognised code falls
back to the HTTP status.

| `error_code` | HTTP | Category | SDK exception |
|---|---|---|---|
| `WF_BUDGET_EXCEEDS_ORG_BUDGET` | 200 | `budget` | — |
| `BUSINESS_IMPACT_INVALID` | 400 | `infra` | `NullRunBlockedException` |
| `CHAIN_ID_INVALID` | 400 | `infra` | `NullRunChainError` |
| `EXECUTION_ID_MALFORMED` | 400 | `infra` | `NullRunBackendError` |
| `EXECUTION_ID_REQUIRED` | 400 | `infra` | `NullRunBackendError` |
| `INVALID_EXECUTION_ID` | 400 | `infra` | `NullRunBackendError` |
| `MODEL_REQUIRED` | 400 | `infra` | `NullRunBlockedException` |
| `PROTOCOL_HEADER_INVALID` | 400 | `infra` | `NullRunProtocolError` |
| `PROTOCOL_HEADER_REQUIRED` | 400 | `infra` | `NullRunProtocolError` |
| `PROTOCOL_TOO_NEW` | 400 | `infra` | `NullRunProtocolError` |
| `PROTOCOL_TOO_OLD` | 400 | `infra` | `NullRunProtocolError` |
| `VALIDATION_FAILED` | 400 | `infra` | `NullRunBlockedException` |
| `WORKFLOW_ID_BODY_MISMATCH` | 400 | `infra` | `NullRunBackendError` |
| `API_KEY_DISABLED` | 401 | `infra` | `NullRunAuthError` |
| `API_KEY_EXPIRED` | 401 | `infra` | `NullRunAuthError` |
| `API_KEY_INVALID` | 401 | `infra` | `NullRunAuthError` |
| `API_KEY_MALFORMED` | 401 | `infra` | `NullRunAuthError` |
| `API_KEY_MISSING` | 401 | `infra` | `NullRunAuthError` |
| `API_KEY_REVOKED` | 401 | `infra` | `NullRunAuthError` |
| `BUDGET_ANTI_DOS_RESERVED_CAP` | 402 | `budget` | `NullRunBudgetError` |
| `BUDGET_CACHE_EXCEEDED` | 402 | `budget` | `NullRunBudgetError` |
| `BUDGET_HARD_BLOCKED` | 402 | `budget` | `NullRunBudgetError` |
| `BUDGET_ORG_CEILING_BLOCKED` | 402 | `budget` | `NullRunBudgetError` |
| `BUDGET_OVERDRAFT_EXCEEDED` | 402 | `budget` | `NullRunBudgetError` |
| `BUDGET_PERIOD_NOT_STARTED` | 402 | `budget` | `NullRunBudgetError` |
| `BUDGET_RECHECK_FAILED` | 402 | `infra` | `NullRunBudgetRecheckFailedError` |
| `BUDGET_REDIS_UNAVAILABLE` | 402 | `infra` | `NullRunBudgetError` |
| `BUDGET_SOFT_BLOCKED` | 402 | `budget` | `NullRunBudgetError` |
| `BUDGET_WORKFLOW_BLOCKED` | 402 | `budget` | `NullRunBudgetError` |
| `CHAIN_MAX_DURATION_EXCEEDED` | 402 | `halt` | `NullRunChainError` |
| `EXECUTION_QUOTA_EXCEEDED` | 402 | `budget` | `NullRunBlockedException` |
| `RESERVED_SCANNED_PARTIAL` | 402 | `budget` | `NullRunBudgetError` |
| `APPROVAL_DENIED` | 403 | `denied` | `NullRunApprovalDeniedError` |
| `APPROVAL_EXPIRED` | 403 | `denied` | `NullRunApprovalExpiredError` |
| `APPROVAL_NOT_YET_APPROVED` | 403 | `denied` | `NullRunApprovalNotYetApprovedError` |
| `APPROVAL_TOOL_ARGUMENT_MISMATCH` | 403 | `infra` | `NullRunApprovalDigestMismatchError` |
| `APPROVAL_TOOL_ARGUMENT_UNAVAILABLE` | 403 | `infra` | `NullRunApprovalDbUnavailableError` |
| `CHAIN_CROSS_ORG` | 403 | `infra` | `NullRunChainError` |
| `CHAIN_KEY_MISMATCH` | 403 | `infra` | `NullRunChainError` |
| `CHAIN_ORG_MISMATCH` | 403 | `infra` | `NullRunChainError` |
| `CIRCUIT_BREAKER_TRIPPED` | 403 | `halt` | `NullRunBlockedException` |
| `EXECUTION_KEY_MISMATCH` | 403 | `infra` | `NullRunAuthError` |
| `EXECUTION_ORG_MISMATCH` | 403 | `infra` | `NullRunAuthError` |
| `INSUFFICIENT_SCOPE` | 403 | `infra` | `NullRunAuthError` |
| `MCP_APPROVAL_REQUIRED` | 403 | `denied` | `NullRunMcpApprovalRequiredError` |
| `MCP_DEFINITION_DRIFTED` | 403 | `denied` | `NullRunApprovalToolDigestMismatchError` |
| `MCP_DESTRUCTIVE_BLOCKED` | 403 | `denied` | `NullRunMcpDestructiveBlockedError` |
| `MCP_READONLY_BYPASS_BLOCKED` | 403 | `denied` | `NullRunMcpReadonlyBypassBlockedError` |
| `MCP_TOOL_APPROVAL_REQUIRED` | 403 | `denied` | `NullRunMcpApprovalRequiredError` |
| `MCP_TOOL_BLOCKED` | 403 | `denied` | `NullRunToolBlockedError` |
| `MCP_TOOL_DECISION_REQUIRED` | 403 | `denied` | `NullRunMcpApprovalRequiredError` |
| `MCP_TOOL_REMOVED` | 403 | `denied` | `NullRunToolBlockedError` |
| `ORG_MISMATCH` | 403 | `infra` | `NullRunAuthError` |
| `PARENT_EXECUTION_KEY_MISMATCH` | 403 | `infra` | `NullRunChainError` |
| `PARENT_EXECUTION_ORG_MISMATCH` | 403 | `infra` | `NullRunChainError` |
| `TOOL_BLOCKED` | 403 | `denied` | `NullRunToolBlockedError` |
| `WORKFLOW_INACTIVE` | 403 | `halt` | `NullRunWorkflowInactiveError` |
| `WORKFLOW_PAUSED` | 403 | `halt` | `NullRunBlockedException` |
| `APPROVAL_NOT_FOUND` | 404 | `infra` | `NullRunApprovalDbUnavailableError` |
| `CHAIN_NOT_FOUND` | 404 | `halt` | `NullRunChainError` |
| `EXECUTION_NOT_FOUND` | 404 | `infra` | `NullRunExecutionNotFoundError` |
| `PARENT_EXECUTION_NOT_FOUND` | 404 | `infra` | `NullRunChainError` |
| `SUBWORKFLOW_INVOKE_DISABLED` | 404 | `denied` | `NullRunChainError` |
| `APPROVAL_ALREADY_DECIDED` | 409 | `infra` | `NullRunApprovalReplayRejectedError` |
| `APPROVAL_CONFLICT` | 409 | `infra` | `NullRunApprovalDbUnavailableError` |
| `APPROVAL_DIGEST_MISMATCH` | 409 | `infra` | `NullRunApprovalDigestMismatchError` |
| `APPROVAL_REPLAY_REJECTED` | 409 | `infra` | `NullRunApprovalReplayRejectedError` |
| `APPROVAL_TOOL_DIGEST_MISMATCH` | 409 | `infra` | `NullRunApprovalToolDigestMismatchError` |
| `APPROVAL_TOOL_MISMATCH` | 409 | `infra` | `NullRunApprovalToolMismatchError` |
| `CHAIN_ENDED` | 409 | `halt` | `NullRunChainError` |
| `IDEMPOTENCY_CONFLICT` | 409 | `infra` | `NullRunProtocolError` |
| `IDEMPOTENCY_IN_FLIGHT` | 409 | `infra` | `NullRunBackendError` |
| `IDEMPOTENCY_KEY_MISMATCH` | 409 | `infra` | `NullRunProtocolError` |
| `BATCH_TOO_LARGE` | 413 | `infra` | `NullRunBackendError` |
| `CONSUME_OVERBUDGET` | 422 | `budget` | `NullRunConsumeOverbudgetError` |
| `CONTROL_CHARS_IN_FIELD` | 422 | `infra` | `NullRunBackendError` |
| `EXECUTION_NOT_BOUND` | 422 | `infra` | `NullRunExecutionNotFoundError` |
| `LEGACY_GRANT_REJECTED` | 422 | `infra` | `NullRunBlockedException` |
| `WORKFLOW_CYCLE_DETECTED` | 422 | `infra` | `NullRunChainError` |
| `WORKFLOW_DEPTH_EXCEEDED` | 422 | `infra` | `NullRunChainError` |
| `WORKFLOW_PARENT_BINDING_EXPIRED` | 422 | `infra` | `NullRunChainError` |
| `BUDGET_EXCEEDED` | 429 | `budget` | `NullRunBudgetError` |
| `LOOP_DETECTED` | 429 | `denied` | `NullRunBlockedException` |
| `RATE_LIMIT_EXCEEDED` | 429 | `budget` | `RateLimitError` |
| `RATE_LIMIT_PLAN_TIER` | 429 | `budget` | `RateLimitError` |
| `TOO_MANY_PENDING_APPROVALS` | 429 | `budget` | `NullRunBlockedException` |
| `WAITLIST_RATE_LIMITED` | 429 | `denied` | `RateLimitError` |
| `APPROVAL_CREATE_FAILED` | 500 | `infra` | `NullRunApprovalDbUnavailableError` |
| `APPROVAL_DIGEST_RECOMPUTE_FAILED` | 500 | `infra` | `NullRunApprovalDbUnavailableError` |
| `APPROVAL_PERSISTENCE_FAILED` | 500 | `infra` | `NullRunApprovalDbUnavailableError` |
| `APPROVAL_VALIDATION_FAILED` | 500 | `infra` | `NullRunApprovalDbUnavailableError` |
| `EXECUTION_BINDING_MISSING` | 500 | `infra` | `NullRunBackendError` |
| `INTERNAL_ERROR` | 500 | `infra` | `NullRunBackendError` |
| `WORKFLOW_BUDGET_CONFIG_INVALID` | 500 | `infra` | `NullRunBackendError` |
| `APPROVAL_DB_UNAVAILABLE` | 503 | `infra` | `NullRunApprovalDbUnavailableError` |
| `APPROVAL_RULES_UNAVAILABLE` | 503 | `infra` | `NullRunApprovalDbUnavailableError` |
| `AUTH_BACKEND_UNAVAILABLE` | 503 | `infra` | `NullRunBackendError` |
| `BUDGET_DATA_UNAVAILABLE` | 503 | `infra` | `NullRunBackendError` |
| `BUDGET_PROJECTION_UNAVAILABLE` | 503 | `infra` | `NullRunBackendError` |
| `CIRCUIT_BREAKER_STATE_LOOKUP_FAILED` | 503 | `infra` | `NullRunBackendError` |
| `EXECUTION_BINDING_READ_FAILED` | 503 | `infra` | `NullRunBackendError` |
| `EXECUTION_BINDING_WRITE_FAILED` | 503 | `infra` | `NullRunBackendError` |
| `EXECUTION_RESOLVE_REDIS_ERROR` | 503 | `infra` | `NullRunBackendError` |
| `IDEMPOTENCY_REDIS_UNAVAILABLE` | 503 | `infra` | `NullRunBackendError` |
| `INGESTION_BACKPRESSURE` | 503 | `infra` | `NullRunBackendError` |
| `INGESTION_CLOSED` | 503 | `infra` | `NullRunBackendError` |
| `INVOKE_PERSIST_FAILED` | 503 | `infra` | `NullRunBackendError` |
| `MCP_REGISTRY_UNAVAILABLE` | 503 | `infra` | `NullRunBackendError` |
| `ORG_CONTEXT_UNRESOLVED` | 503 | `infra` | `NullRunBackendError` |
| `POLICY_UNCONFIGURED` | 503 | `infra` | `NullRunBlockedException` |
| `RATE_LIMITER_UNAVAILABLE` | 503 | `infra` | `NullRunRateLimitRedisError` |
| `RATE_LIMIT_PLAN_LOOKUP_FAILED` | 503 | `infra` | `NullRunRateLimitRedisError` |
| `RATE_LIMIT_REDIS_UNAVAILABLE` | 503 | `infra` | `NullRunRateLimitRedisError` |
| `REDIS_UNAVAILABLE` | 503 | `infra` | `NullRunBackendError` |
| `RESERVATION_NOT_FOUND` | 503 | `infra` | `NullRunBackendError` |
| `RESERVE_DISABLED` | 503 | `infra` | `NullRunBackendError` |
| `TOOL_BLOCKED_BACKSTOP_UNAVAILABLE` | 503 | `infra` | `NullRunBackendError` |
| `WORKFLOW_DEPTH_LOOKUP_FAILED` | 503 | `infra` | `NullRunChainError` |
| `WORKFLOW_INACTIVE_LOOKUP_FAILED` | 503 | `infra` | `NullRunBackendError` |

Three codes come from the request parser rather than the registry. They answer
on the enforcement path with `error_code` set to `INVALID_JSON` (400),
`INVALID_FIELD` (422), or `MISSING_CONTENT_TYPE` (415).

### SDK exception hierarchy

Every public SDK exception inherits from `NullRunError` and carries four
structured fields: `error_code`, `user_action`, `retryable`, and `docs_url`.

```
Exception
└── BreakerError
    ├── BreakerTransportError           events could not be delivered
    │   └── InsecureTransportError     HTTPS was required
    └── NullRunError
        ├── NullRunDecision                  marker — expected policy outcomes
        │   ├── NullRunBlockedException      NR-X001
        │   │   ├── NullRunDeniedError                        NR-D001
        │   │   ├── NullRunBudgetError                        NR-B004
        │   │   │   └── NullRunBudgetRecheckFailedError        NR-B006
        │   │   ├── NullRunToolBlockedError                   NR-T001
        │   │   ├── NullRunApprovalDbUnavailableError         NR-A016
        │   │   ├── NullRunApprovalResponseMissingError       NR-A004
        │   │   ├── NullRunApprovalNotYetApprovedError        NR-A010
        │   │   ├── NullRunApprovalDeniedError                NR-A011
        │   │   ├── NullRunApprovalExpiredError               NR-A012
        │   │   ├── NullRunApprovalReplayRejectedError        NR-A015
        │   │   ├── NullRunApprovalDigestMismatchError        NR-A013
        │   │   ├── NullRunApprovalToolDigestMismatchError    NR-A014
        │   │   ├── NullRunApprovalToolMismatchError          NR-A017
        │   │   ├── NullRunMcpDestructiveBlockedError         NR-MCP01
        │   │   ├── NullRunMcpReadonlyBypassBlockedError      NR-MCP02
        │   │   └── NullRunMcpApprovalRequiredError           NR-MCP03
        │   ├── NullRunConsumeOverbudgetError                 NR-O001
        │   ├── NullRunChainError                             NR-CH001
        │   ├── WorkflowPausedException                       NR-W003
        │   └── NullRunWorkflowInactiveError                  NR-W004
        ├── WorkflowKilledInterrupt          NR-W002 — not a NullRunDecision
        │   └── NullRunWorkflowKilledError   NR-W002
        └── NullRunInfrastructureError       marker — system failures
            ├── NullRunConfigError                          NR-C000
            ├── NullRunAuthenticationError                  NR-A001
            │   └── NullRunAuthError                        NR-A003
            ├── NullRunProtocolError                        NR-P001
            │   └── NullRunMalformedGateResponseError       NR-P002
            ├── NullRunGateIndeterminateError               NR-P004
            ├── NullRunUnknownActionError                   NR-P005
            ├── NullRunUnclassifiedRefusalError             NR-P003
            ├── NullRunRateLimitRedisError                  NR-R002
            └── NullRunTransportError                       NR-B001
                ├── NullRunBackendError                     NR-B002
                │   └── NullRunExecutionNotFoundError       NR-EX01
                └── RateLimitError                          NR-R001
```

Three classes sit outside the marker split, and each one matters when you
write an `except` chain.

- `WorkflowKilledInterrupt` inherits from `NullRunError` directly, not from
  `NullRunDecision`. A kill is not a policy decision, so
  `except NullRunDecision` does not catch it. Catch it by name.
- `NullRunApprovalDbUnavailableError` inherits from
  `NullRunBlockedException`, so it lands in the decision branch even though an
  unreachable approval store is a system failure. Its `error_code`
  (`NR-A016`) is what distinguishes it.
- `BreakerTransportError` and `InsecureTransportError` inherit from
  `BreakerError`, not from `NullRunError`. `except NullRunError:` does not
  catch them.

`NullRunUnclassifiedRefusalError` lives in the SDK's category module, not the
exception module. It is still importable from the package.

`NullRunBlockedException` carries `.workflow_id`, `.reason`, `.action`,
`.tool_name`, `.status_code`, and `.details`. It has **no** `.message`
attribute — use `str(exc)`.

### Decision vs. infrastructure

The hierarchy splits `NullRunError` into two marker subclasses by what kind of
event the exception represents. The split is additive: every existing
`except NullRunError:` and `except NullRunBlockedException:` clause keeps
matching.

| Marker | What it covers | Why it matters |
|---|---|---|
| `NullRunDecision` | Expected policy outcomes — budget cap, tool block, chain rejection, loop detection, workflow pause, over-budget commit. | The enforcement layer did its job. UX explains the decision and, where it applies, offers an upgrade or an alternative action. |
| `NullRunInfrastructureError` | System failures — network unreachable, gateway 5xx, gateway 429, auth rejection, config error, rate limiter down. | The SDK could not reach or query the policy engine. UX is a generic "service unavailable". Operators triage with `error_code`, `retryable`, and for transport errors `source` and `endpoint`. |

Rate limits land on the infrastructure side. A 429 arrives as `RateLimitError`,
a subclass of `NullRunTransportError` → `NullRunInfrastructureError`. Handle it
as a system failure with a retry, and surface `upgrade_url` when the user
genuinely needs a higher plan.

`WorkflowKilledInterrupt` belongs to neither marker. Catch it by name ahead of
both.

#### Recommended handler shape

```python title="decision_vs_infra_handler.py"
import nullrun
from nullrun.breaker.exceptions import (
    NullRunDecision,
    NullRunInfrastructureError,
)

try:
    result = run_the_agent(message)
except NullRunDecision as exc:
    # Expected. Surface it to the user and tag it with the code.
    logger.info("nullrun_decision code=%s", exc.error_code)
    return nullrun.format_user_message(exc)
except NullRunInfrastructureError as exc:
    # System failure. Alert ops and retry with backoff.
    logger.exception("nullrun_infrastructure code=%s", exc.error_code)
    return nullrun.format_user_message(exc)
```

#### Mapping decisions to HTTP status

The gateway answers a refusal with its own status. A host that re-exposes the
failure to its own clients picks its own status.

The SDK's FastAPI integration ships one mapping. It keys on the `error_code`,
not on the exception class.

| `error_code` | Status | Meaning |
|---|---|---|
| `NR-B004` | 429 | Budget exhausted. |
| `NR-L001` | 429 | Loop detected. |
| `NR-R001` | 429 | Rate limited. |
| `NR-T001` | 403 | Tool blocked. |
| `NR-X001` | 403 | Generic block. |
| `NR-W003` | 503 | Workflow paused. |
| `NR-W002` | 503 | Workflow killed. |
| any other decision code | 429 | Default for a decision. |
| any infrastructure code | 503 | Default for a system failure. |

`NR-W003` surfaces `resume_after` as the `Retry-After` header. `NR-R001`
surfaces `retry_after` the same way.

`.status_code` carries the gateway's own status on the exceptions that
received one: the `NullRunBlockedException` family,
`NullRunConsumeOverbudgetError`, and `NullRunChainError`. Read it with
`getattr(exc, "status_code", None)` when you need the wire status.

See [Use with FastAPI](#64-use-with-fastapi) for the reference integration.

### HTTP status summary

| Status | Meaning | SDK action |
|---|---|---|
| 200 | OK | — |
| 400 | Bad request | Inspect `message`, fix the request. |
| 401 | Bad API key or signature | Refresh the key, check the signing secret. |
| 402 | Budget refused | Stop. Do not retry. |
| 403 | Forbidden | Check the role, scope, or org. |
| 404 | Not found | The caller handles it. |
| 409 | Conflict | Inspect `message` and `details`. |
| 413 | Body too large | Split the batch. |
| 415 | Unsupported media type | Send `Content-Type: application/json`. |
| 422 | Validation or plan limit | Inspect `details`. |
| 429 | Rate limit | Honour `Retry-After`; check `upgrade_url`. |
| 5xx | Gateway error | Retry with backoff. |

When the gateway is unreachable, the SDK raises `NullRunTransportError` with
`source` set to `NETWORK_ERROR` when the request never left the process, and
`GATEWAY_ERROR` when the gateway answered.

### NR-* error code catalog

Stable, machine-readable identifiers on every SDK exception.

- **Decision and enforcement codes** — what the gate decided. Surfaced as
  `NullRunDecision` subclasses.
- **Infrastructure codes** — transport, backend, and config failures.
  Surfaced as `NullRunInfrastructureError` subclasses.

`—` in the HTTP column means the SDK raised the error locally, with no wire
status attached.

#### Decision and enforcement codes

| `error_code` | When | HTTP | SDK class |
|---|---|---|---|
| `NR-D001` | The operator refused this specific call. Only raised when `init(on_denied="message")` is set. | — | `NullRunDeniedError` |
| `NR-X001` | A policy block with no more specific code. | — | `NullRunBlockedException` |
| `NR-B004` | The workflow budget is exhausted. | 402 | `NullRunBudgetError` |
| `NR-B006` | The budget moved between the gate call and the execute call. | 402 | `NullRunBudgetRecheckFailedError` |
| `NR-L001` | The same tool repeated past the per-policy threshold. | 429 | `NullRunBlockedException` |
| `NR-O001` | The actual cost exceeded the reservation. | 422 | `NullRunConsumeOverbudgetError` |
| `NR-T001` | The tool is in the block list. | 403 | `NullRunToolBlockedError` |
| `NR-T003` | An MCP tool call was blocked by the gate, and the client was not invoked. | — | `NullRunBlockedException` |
| `NR-CH001` | The chain scope check failed — bad chain id, wrong parent, or the max duration exceeded. | 402 or 403 | `NullRunChainError` |
| `NR-EX01` | The execution id is unknown or its binding expired. | 404 | `NullRunExecutionNotFoundError` |
| `NR-W002` | The operator killed the workflow. | — | `NullRunWorkflowKilledError` (alias `WorkflowKilledInterrupt`) |
| `NR-W003` | The workflow is paused. | — | `WorkflowPausedException` |
| `NR-W004` | The workflow is inactive. | 403 | `NullRunWorkflowInactiveError` |
| `NR-A004` | The gate asked for approval and returned no approval id. | — | `NullRunApprovalResponseMissingError` |
| `NR-A010` | The operator has not decided yet. | 403 | `NullRunApprovalNotYetApprovedError` |
| `NR-A011` | The operator denied the approval. | 403 | `NullRunApprovalDeniedError` |
| `NR-A012` | The approval expired. | 403 | `NullRunApprovalExpiredError` |
| `NR-A013` | The action changed since the approval. | 409 | `NullRunApprovalDigestMismatchError` |
| `NR-A014` | The tool surface changed since the approval. | 409 | `NullRunApprovalToolDigestMismatchError` |
| `NR-A015` | The grant was already consumed. | 409 | `NullRunApprovalReplayRejectedError` |
| `NR-A016` | The approval store is unreachable. Fails closed. | 503 | `NullRunApprovalDbUnavailableError` |
| `NR-A017` | The executing tool is outside the approved tool set. | 409 | `NullRunApprovalToolMismatchError` |
| `NR-MCP01` | A destructive MCP tool was blocked. | 403 | `NullRunMcpDestructiveBlockedError` |
| `NR-MCP02` | A read-only MCP tool was blocked. | 403 | `NullRunMcpReadonlyBypassBlockedError` |
| `NR-MCP03` | An MCP tool needs operator approval. | 403 | `NullRunMcpApprovalRequiredError` |

The approval codes are most often seen inside a running agent flow: the SDK
parked for human review, and the operator acted or the grant aged out. Match
the specific subclass first, and fall back to `NullRunBlockedException` when
the exact cause does not matter.

#### Infrastructure codes

| `error_code` | When | HTTP | SDK class |
|---|---|---|---|
| `NR-B001` | The request never reached the gateway — timeout, connection error, or DNS failure. | — | `NullRunTransportError` |
| `NR-B002` | The gateway returned 5xx. | 500 or 503 | `NullRunBackendError` |
| `NR-R001` | The gateway returned 429 with a `Retry-After`. | 429 | `RateLimitError` |
| `NR-R002` | The rate limiter is unavailable. Fails closed. | 503 | `NullRunRateLimitRedisError` |
| `NR-C000` | The SDK is misconfigured. | — | `NullRunConfigError` |
| `NR-C001` | No API key is available — `NULLRUN_API_KEY` is unset and none was passed to `init()`. | — | `NullRunAuthenticationError` |
| `NR-A001` | The credentials were rejected. | 401 or 403 | `NullRunAuthenticationError` |
| `NR-A002` | The key verification answered 200 but carried no organization id. | — | `NullRunAuthenticationError` |
| `NR-A003` | The API key was rejected. | 401 | `NullRunAuthError` |
| `NR-S001` | A development bypass or a removed execution mode was requested. | — | `NullRunConfigError` |
| `NR-P001` | The wire-protocol version does not match the gateway's. | 400 | `NullRunProtocolError` |
| `NR-P002` | The gate response is not a decision the SDK can act on. | — | `NullRunMalformedGateResponseError` |
| `NR-P003` | The refusal carried a category the SDK does not understand, so the SDK cannot tell a policy outcome from a backend fault. | — | `NullRunUnclassifiedRefusalError` |
| `NR-P004` | The SDK could not obtain a decision, and it did not assume one. | — | `NullRunGateIndeterminateError` |
| `NR-P005` | The control plane sent an action type this SDK cannot run. | — | `NullRunUnknownActionError` |
| `NR-T-PARSE` | The gateway response body could not be parsed as JSON. | — | `NullRunTransportError` |

`NR-P003` and `NR-P004` are retryable. `NR-P002` is retryable once the
connection path is fixed. `NR-P001` and `NR-P005` are not.

### See also

- [Concepts → Error handling](#43-error-handling)
- [SDK API](#71-sdk-api)
- [SDK API → User-facing messages](#71-sdk-api)
- [Use with FastAPI](#64-use-with-fastapi)
- [HTTP API](#73-http-api)
- [Circuit breaker](#21-circuit-breaker)
- [Sensitive tools](#24-sensitive-tools)


## 7.6 Tool catalog

A reference list of the tool names LLM agents commonly expose, tagged
with a risk rating you can use as a starting point when you configure
`ToolBlock` patterns.

`@protect` is the entry point for every protected tool. The tool name
and the call's argument bag both reach the gateway, so a rule can match
on the name and a typed approval rule can read an argument value.

| Rating | Meaning |
| --- | --- |
| `low` | Read-only or reversible. Safe to call without a policy decision. |
| `medium` | Mutates external state, and the change is reversible — an issue created, a draft email, an object stored. |
| `high` | **Side effects you cannot easily undo** — a file written or deleted, money moved, a message sent, code executed, infrastructure changed. Mark it with `@protect` and route it through an approval rule. |

The rating is a starting point, not an enforced value. The gateway
does not carry a risk table; it matches the names you write into a
policy.

### Search & retrieval

| Tool | Risk |
| --- | --- |
| `tavily_search`, `tavily_search_results_json` | low |
| `duckduckgo_search`, `duckduck_results_json` | low |
| `google_search`, `google_search_results_json` | low |
| `bing_search` | low |
| `brave_search` | low |
| `web_search`, `search_web` | low |
| `fetch`, `fetch_url` | low |
| `requests_get` | low |
| `wikipedia`, `arxiv`, `pubmed_search`, `semantic_scholar` | low |
| `news_search`, `search_news` | low |
| `requests_post`, `requests_put`, `requests_patch` | medium |
| `requests_delete` | high |

### File system

| Tool | Risk |
| --- | --- |
| `read_file`, `file_read` | low |
| `list_directory`, `get_file_info`, `search_files`, `file_search` | low |
| `copy_file`, `create_directory` | medium |
| `write_file`, `file_write`, `create_file`, `edit_file` | high |
| `delete_file`, `file_delete`, `move_file` | high |

### Code execution

Any tool that evaluates arbitrary code is `high` by definition. The
blast radius is the whole host or sandbox the agent reaches.

`python_repl`, `python_repl_ast`, `execute_python`,
`code_interpreter`, `e2b_code_interpreter`, `execute_javascript`,
`execute_code`, `run_command`, `run_bash_command`, `terminal`, `bash`,
`shell`, `repl` — all **`high`**. Cover them with one pattern per
family rather than enumerating every framework's code runner.

### Databases

| Tool | Risk |
| --- | --- |
| `sql_db_schema`, `sql_db_query_checker`, `read_query` | low |
| `list_tables`, `describe_table` | low |
| `sql_db_query`, `query_sql_database`, `db_query` | medium |
| `redis_set` | medium |
| `execute_sql`, `run_sql`, `db_write`, `write_query`, `create_table` | high |
| `db_delete`, `redis_delete` | high |

### Git & GitHub

| Tool | Risk |
| --- | --- |
| `git_status`, `git_diff`, `git_log` | low |
| `github_get_issue`, `github_get_pull_request`, `github_list_repos`, `github_get_file`, `github_search_code` | low |
| `github_create_issue`, `github_update_issue`, `github_close_issue`, `github_create_pull_request`, `github_create_repo`, `github_create_branch`, `git_add`, `git_checkout` | medium |
| `git_commit`, `github_merge_pull_request`, `github_push_files`, `github_delete_repo` | high |

### Email & messaging

| Tool | Risk |
| --- | --- |
| `gmail_get_message`, `gmail_search`, `office365_search_emails`, `slack_get_channel`, `slack_get_messages` | low |
| `gmail_create_draft`, `office365_create_draft` | medium |
| `send_email`, `send_gmail`, `gmail_send_message`, `gmail_delete_message`, `office365_send_email`, `slack_send_message`, `slack_schedule_message`, `send_sms` | high |

### Calendar & tasks

| Tool | Risk |
| --- | --- |
| `office365_search_events`, `get_calendar_events` | low |
| `office365_create_event`, `create_calendar_event`, `create_task`, `complete_task` | medium |
| `delete_calendar_event`, `delete_task` | high |

### Cloud & infrastructure

| Tool | Risk |
| --- | --- |
| `s3_get_object`, `s3_list_objects`, `ec2_describe_instances`, `kubernetes_get` | low |
| `s3_put_object`, `docker_run` | medium |
| `s3_delete_object`, `s3_delete`, `ec2_start_instance`, `ec2_stop_instance`, `ec2_terminate_instance`, `lambda_invoke`, `kubernetes_apply`, `kubernetes_delete`, `docker_stop` | high |

### Finance & payments

`stripe_charge`, `stripe_create_customer`, `stripe_refund`,
`stripe_create_payment`, `create_invoice`, `send_payment` — all
**`high`**. Read-only calls (`get_balance_sheet`,
`get_income_statement`, `get_cash_flow`) drop to `low`.

### Memory & vector stores

| Tool | Risk |
| --- | --- |
| `vector_store_search`, `memory_retrieve`, `search_nodes` | low |
| `vector_store_add`, `memory_store`, `create_entities`, `add_observations` | medium |
| `vector_store_delete`, `memory_delete`, `delete_entities` | high |

### Browser & scraping

| Tool | Risk |
| --- | --- |
| `puppeteer_screenshot`, `browser_screenshot`, `scrape_page`, `extract_content` | low |
| `puppeteer_navigate`, `puppeteer_click`, `puppeteer_fill`, `browser_navigate`, `browser_click` | medium |
| `puppeteer_evaluate` | high |

`puppeteer_evaluate` runs JavaScript in the page, so it can make
cross-origin requests, inject DOM, and read credentials. Treat it as
`high`. `browser_navigate` and `browser_click` are `medium` because
they act on whatever URL the agent picks.

### MCP tools

An MCP tool's name is whatever the server exposes. The SDK sends that
name to the gateway unchanged, so a `ToolBlock` pattern has to spell it
the way the server does. The **MCP servers** view in the control center
lists the servers and the tools each one registers — read the names off
there rather than guessing them from the server's documentation.

### Recommended ToolBlock starter list

The SDK keeps a built-in set of sensitive tool names — `stripe.charge`,
`send_email`, `db.delete` and similar. `runtime.get_sensitive_tools()`
returns that set plus any tool registered with
`runtime.register_sensitive_tools(...)`. The set classifies names. It
blocks nothing on its own. A tool is blocked by a `ToolBlock` policy,
and the gateway evaluates that policy on every gate call.

Create the policy in the control center under **Governance → Policies → New
policy**, and pick **Tool block** as the type. The control center renders
the canonical tool name for every framework integration, so you can
match against the right string.

The same policy as a `POST /api/v1/orgs/{org_id}/policies` body:

```json title="tool_block_policy.json"
{
  "name": "Sensitive starter (matches the catalog)",
  "policy_type": "tool_block",
  "scope": "org",
  "config": {
    "tool_pattern": [
      "stripe*", "charge", "send_payment", "create_invoice", "refund",
      "send_email", "send_gmail", "send_message", "send_sms",
      "slack_send*", "office365_send*",
      "delete_file", "file_delete", "write_file", "file_write",
      "execute_sql", "run_sql", "db_write", "db_delete",
      "write_query", "create_table",
      "s3_delete*", "ec2_terminate*", "ec2_stop*",
      "lambda_invoke", "kubernetes_delete", "kubernetes_apply",
      "python_repl*", "bash", "shell", "terminal",
      "execute_*", "run_command", "run_bash_command",
      "git_commit", "github_merge*", "github_push*", "github_delete*",
      "memory_delete", "vector_store_delete", "delete_entities"
    ]
  }
}
```

`tool_pattern` holds an array of strings. One bare string is rejected
with `422`.

Note the trailing `*` on the family patterns. `stripe*` covers
`stripe_charge`, `stripe_refund` and every other `stripe_…` name.
`stripe.*` does not: it matches the bare name `stripe` and dotted
names like `stripe.charge`, and nothing else.

### Pattern syntax

`*` is the only metacharacter. There is no regex.

| Pattern | Matches | Does not match |
| --- | --- | --- |
| `bash` | `bash` | `bash_foo`, `pybash` |
| `bash*` | `bash`, `bash_foo`, `bash.foo` | `pybash` |
| `*.secret` | `aws.secret`, `db.secret` | `secret` |
| `bash.*` | `bash`, `bash.foo`, `bash.foo.bar` | `bash_foo` |
| `*.drop_*` | `s3.drop_table`, `db.drop_user` | `s3.execute_drop` |

Alternatives share one entry. The pipe character separates them, and
each side is evaluated on its own:

```text
bash|sh|shell
```

That entry matches `bash`, `sh` and `shell`, and nothing else.

| Rule | Behaviour |
| --- | --- |
| No `*` | Exact equality. A bare literal is never a substring match. |
| One `*` | Anchored prefix and/or suffix. `db.drop_*` needs the prefix; `*.secret` needs the suffix. |
| Two or more `*` | Every literal segment must appear in the value, in order. The ends stay anchored when the pattern does not start or end with `*`. |
| `prefix.*` | The bare prefix **and** any dotted continuation. `bash.*` covers `bash`, `bash.foo` and `bash.foo.bar`. It does not cover `bash_foo`. |
| `\|` | Separates alternatives inside one entry. Each alternative is evaluated on its own. |
| `?` | An ordinary character, not a single-character wildcard. |
| `*` alone | Matches every tool name. |
| `**` | Matches nothing. The policy is accepted, but the pattern never matches a tool. |
| Empty | Matches nothing. |

Matching is case-sensitive. A built-in tool name is lowercase ASCII
letters, digits, `_` and `-`, up to 64 bytes, so write the pattern
in the same shape.

### What a pattern cannot do

Matching reads the tool name only. A pattern never inspects the
arguments, so `bash*` blocks every bash call whatever the command
inside it, and no glob can express a condition on one argument.

For a rule that depends on an argument — "block refunds over $500",
"approve only sends to `@internal` addresses" — use the typed
predicates on an approval rule. See
[Human approval → typed predicates](#32-human-approval).

### Other limits

| Limit | Value |
| --- | --- |
| Pattern length | 4096 bytes per entry |
| Pattern characters | No control characters. A pattern with a newline is refused when you save the policy. |
| Enforcement | A tool block is always hard. Soft budget mode does not soften it. |

### See also

- [Tool policies](#23-tool-policies) — how a `ToolBlock` policy is evaluated
- [Sensitive tools](#24-sensitive-tools) — the policy-driven way to express "this tool needs review"
- [Human approval](#32-human-approval) — typed predicates for narrower rules


## 7.7 Glossary

The vocabulary NullRun uses, in one place. Each entry says what the
term means and links to the page that goes deeper on it.

### Enforcement

**Gate**
:   The check that runs before a supported tool or model call executes.
    It returns one of three decisions — `allow`, `block`, or
    `require_approval` — and it is the only thing standing between an
    agent's intent and its side effects. See
    [Circuit breaker](#21-circuit-breaker).

**Policy**
:   A rule attached to your organization or to a single workflow. Each
    policy answers one enforcement question, and the applicable ones
    are aggregated most-restrictive-wins across scopes. There are three
    types — `budget_limit`, `rate_limit`, and `tool_block`. See
    [Policies](#22-policies).

**ToolBlock**
:   The policy type that decides which tools an agent may call. Its
    patterns are glob matches over canonical tool names, unioned across
    every scope that applies. It is **always hard**: a transport error
    refuses the call regardless of the budget's `enforcement_mode`. See
    [Tool policies](#23-tool-policies).

**Sensitive tool**
:   A tool that should never run without a human paying attention —
    sending mail, moving money, deleting a record. The SDK keeps a
    registry of common sensitive tool names, but the registry enforces
    nothing. Sensitivity is enforced by server-side rules: `ToolBlock`
    patterns and approval rules. See
    [Sensitive tools](#24-sensitive-tools).

**Fail-closed / fail-open**
:   What happens when the gate cannot get the signal it needs. On the
    gateway the enforcement path fails **closed**: a failure to evaluate
    the budget or the per-organization rate limit refuses the call. In
    the SDK the tool-policy gate also fails
    **closed**, so a protected body does not run when the policy engine
    cannot be reached. Two SDK checks fail **open**: the budget
    pre-flight skips the check and logs a warning when the gateway is
    unreachable, then corrects the spend in the tracked events, and the
    control-plane check treats an unreachable gateway as a normal
    workflow. See [Policies](#22-policies) and
    [Circuit breaker](#21-circuit-breaker).

**Circuit breaker**
:   The SDK-side guard that short-circuits event flushes after repeated
    infrastructure failures, so an unreachable gateway does not turn
    into a hang. It opens on transport errors and closes again after a
    cooldown. It does not sit on the gate path, and a protected call is
    never blocked by it. See [Circuit breaker](#21-circuit-breaker).

**Protocol version**
:   The wire contract version the SDK sends on every gateway request in
    the `X-NULLRUN-PROTOCOL` header. The SDK sends version `4`. The
    gateway refuses a request whose version it does not support. See
    [HTTP API](#73-http-api).

### Cost

**Budget**
:   The maximum a workflow may spend in one period. Amounts are in
    cents. See [Budgets](#31-budgets).

**Enforcement mode**
:   Whether a budget blocks hard or soft. `Hard` refuses the call once
    the projected cost exceeds what is left. `Soft` allows a bounded
    overdraft, but only when all three hold: the policy is set to
    `Soft`, an active `chain_id` exists, and the cost stays inside the
    overdraft cap. The cap is the lower of `max_overdraft_cents` and
    `max_overdraft_percent`. When the cap is exhausted the chain is
    marked exhausted and further `Soft` calls on it are refused. See
    [Budgets](#31-budgets).

**execution_id**
:   The id the gateway mints for one tool call. It is a UUIDv7, so ids
    sort by time, and the gateway — not the client — issues it. The
    gateway binds it to your organization and API key, so a call can
    only be settled by the identity that reserved it. See
    [HTTP API](#73-http-api).

**Reservation**
:   The amount a workflow commits at gate time, before the call runs.
    The actual cost is consumed against it afterwards, so the reserve /
    consume invariant keeps a single call from being implicitly
    re-reserved. See [Budgets](#31-budgets).

**Consume**
:   The settlement of a reservation after the call runs. The consumed
    amount may not exceed the reserved amount plus a small fixed
    tolerance. A call that overshoots is refused. See
    [Budgets](#31-budgets).

**operation_id**
:   The id the SDK attaches to one gate call, so several calls in the
    same scope stay distinguishable from one another. It is a client
    value and carries no authority of its own. See
    [HTTP API](#73-http-api).

### Runtime

**Workflow**
:   One agent you run. Each workflow carries its own budget, its own API
    keys, and its own policies, and its cost binds to it as a logical
    unit rather than to a single session. See
    [Workflow context](#41-workflow-context).

**Chain**
:   A group of workflows that run as one logical unit under a shared
    chain context, so a kill or an overrun surfaces across the rest. A
    chain that exceeds its max duration is rejected by the gate with
    `CHAIN_MAX_DURATION_EXCEEDED`. See
    [Workflow context](#41-workflow-context).

**Action**
:   One concrete operation an agent wants to perform — a tool call or a
    model call, with its arguments. The unit the gate evaluates and the
    unit an approval is bound to. See
    [Human approval](#32-human-approval).

**Action source**
:   The gateway's name for one MCP server (or built-in provider) the SDK
    has talked to. One row in **Governance → Action Sources**. See
    [MCP servers](#45-mcp-servers-action-sources).

**Trace**
:   Everything that happened during one run of your agent: every LLM
    call, every tool call, and how long each took. See
    [Tracing](#42-tracing).

**Span**
:   One node in a trace — a single LLM or tool call, with its timing and
    its correlation ids. Spans nest, and a parent trace id propagates
    across a workflow so the control center renders a true waterfall. See
    [Tracing](#42-tracing).

### Control

**Approval**
:   A human decision that lets one specific action run. The grant is
    bound to the exact action payload through a SHA-256
    `action_digest`; if the payload drifts, the grant is refused. See
    [Human approval](#32-human-approval).

**Approval rule**
:   A rule that asks for a human instead of answering `allow` or
    `block` on its own. It is not a fourth policy type: it sits beside
    the policies and matches tool patterns plus a predicate over the
    call's business impact — an amount of money, or a named argument
    value. Approval rules are separate from `ToolBlock`: the tool block
    says which tools are off limits, the approval rule says which calls
    need a person. See [Human approval](#32-human-approval).

**action_digest**
:   The SHA-256 hash that binds an approval to the action it approves.
    A digest mismatch after approval produces a hard block rather than
    letting the substituted action through. See
    [Human approval](#32-human-approval).

**Control plane**
:   The WebSocket channel between the control center and your running agent.
    It is what makes **Kill**, **Pause**, and **Resume** take effect
    immediately rather than on the next gate call. See
    [Control plane](#44-control-plane-websocket).

**Kill**
:   The control-plane signal that stops a workflow. It arrives as
    `WorkflowKilledInterrupt`, which inherits from `NullRunError`
    directly — it is not a policy decision, so
    `except NullRunDecision` does not catch it. See
    [Error handling](#43-error-handling).

**Pause**
:   The control-plane signal that suspends a workflow. It surfaces as
    `WorkflowPausedException` carrying an optional `resume_after`. A
    gate call to a paused workflow is refused with `403`
    `WORKFLOW_PAUSED`. See
    [Error handling](#43-error-handling).


# 8. Compliance


## 8.1 Overview

NullRun sits between an agent and the tools it calls, so it sees the
tool payloads it decides on. This section documents that view: what
data crosses the wire, what is persisted, who can reach it, and what
happens when it is deleted.

| Page | Purpose |
| --- | --- |
| [Data handling & vendor review](#82-data-handling-vendor-review) | The full inventory — what is transmitted, what is stored, retention, sub-processors, and the answers to a standard vendor risk questionnaire. |

!!! info "What NullRun does and does not inspect"

    The gate is a **decision** layer, not a content scanner. It
    evaluates structured metadata about a call — tool name, model,
    declared sensitivity, cost, scope — and returns `allow`,
    `soft_pass`, `require_approval`, `block`, or `deny` before the call
    executes. `soft_pass` lets the call run and books the overspend as
    an overdraft.

    It does not read the free-text arguments of a tool call to decide
    whether the *content* is acceptable. A payload that passes the
    gate because its metadata looked benign is not scanned
    afterwards. Enforce content-level inspection in the agent,
    upstream of NullRun.

    The inverse also holds: the gate never needs a call to have
    completed in order to block it. A decision is returned before
    execution begins, so a blocked call costs nothing and leaves no
    side effect behind.

### See also

- [Data handling & vendor review](#82-data-handling-vendor-review) — the full
  inventory
- [Performance & limits](#92-performance-limits) — timeouts and
  the fail-closed posture
- [API keys](#25-api-keys) — signing, rotation, revocation


## 8.2 Data handling & vendor review

A consolidated answer to the standard vendor-risk questionnaire, for
an employee assessing NULLRUN as a vendor. Every value reflects the
deployed product. Rows marked **Not attested** are honest gaps: the
implementation does not document them.

This page is the detailed companion to the
[Compliance overview](#81-overview). That page gives the short version.

**Reading conventions.** `[V]` = verified · `[D]` = derived or inferred
· `[N]` = not attested.

### At a glance

| Question | Answer | Section |
|---|---|---|
| What does the SDK send? | Tool name, cost estimate, optional typed business impact, optional action digest, and the argument bag. | [Data transmitted](#1-data-transmitted) |
| What does the backend store in Postgres? | Organization, user, key, workflow, policy, approval, cost, and audit rows. The audit table is immutable. | [Data stored](#2-data-stored) |
| What does the backend store in Redis? | Budget counters, execution bindings, rate-limit buckets, session and chain state. The session entries hold the user and organization id. | [Data stored](#2-data-stored) |
| Where is it hosted? | DigitalOcean, with EU regions available. Self-hosted Postgres and Redis on one VPS. | [Hosting](#3-hosting) |
| Who can access production data? | Four role levels. Production shell access through an allowlisted wrapper. | [Access controls](#4-access-controls) |
| How is it encrypted? | TLS at the edge, column-level encryption for Slack OAuth tokens and TOTP secrets, HMAC-SHA256 for request signing and audit exports. | [Encryption](#5-encryption) |
| Which third parties see data? | DigitalOcean, Brevo (DE), Polar (SE), Slack, GitHub, Google. | [Sub-processors](#6-sub-processors) |
| How is data deleted? | Soft-delete with a 60-day grace, then a purge of tenant data. API key revocation is two-phase. | [Deletion](#7-deletion) |
| Where physically is data? | Region selectable at signup. Single-region deployment. | [Residency](#8-data-residency) |
| What is the compliance posture? | A data processing agreement is available at the org endpoint. No SOC 2, ISO 27001, or HIPAA attestation exists. | [Posture](#9-compliance-posture) |

### 1. Data transmitted

#### 1.1 SDK to gateway

The gate request carries:

| Field | Source | Notes |
|---|---|---|
| `execution_id` | Gateway-minted | The gateway **mints a UUIDv7** and echoes it back. A client-supplied id is not honoured for ownership. |
| `trace_id`, `tool`, `mode`, `operation_id` | SDK-supplied | The request envelope. |
| `tool_arguments` | SDK-supplied | The call's argument bag. A `tool_params` field is accepted as an alternative name. A typed approval rule reads a named argument from it. |
| `business_impact` | SDK-supplied | Optional. Required only for typed approval rules. |
| `action_digest` | SDK-supplied | SHA-256 hex of the canonicalised payload. Verified again at execute time. |
| `workflow_id` | SDK-supplied | Must match the workflow bound to the authenticated key, or the request is refused with `WORKFLOW_ID_BODY_MISMATCH`. |

**Organization mismatch guard.** The organization in the body must
match the authenticated context. A mismatch is refused.

**No email address and no actor name** is sent by the SDK.

#### 1.2 SDK to gateway, cost tracking

The cost-tracking request carries the event id, the workflow id, token
counts, the tool or model name, the provider, the model, trace and span
correlation ids, agent and organization ids, latency, retry flag, the
reserved amount, the provider-reported amount, a cost source label, and
free-form metadata.

The cost figure the client sends is **not trusted for enforcement**.
The gateway recomputes it.

#### 1.3 Gateway to SDK

The gate response carries the decision, its source, an explanation, an
approval id when a human is required, the approval timeout, the
server-minted `execution_id`, and an echo of the action digest.

**PII in gate responses:** decision text, the explanation, and
approval ids. No email address, no organization name, no actor
identifier. `[V]`

#### 1.4 Gateway to the LLM provider

- Provider types cover OpenAI, Anthropic, Google, and Azure.
- **NULLRUN does not proxy model calls.** The SDK talks to providers
  directly, using the customer's own API keys. `[D]`
- **Credential invariant:** NULLRUN holds no provider API key. The
  customer's key stays in the customer's process.

#### 1.5 Control plane

- The WebSocket is signed with HMAC-SHA256 over canonical JSON, keyed
  by a per-API-key secret, with a 300-second replay window.
- The receiver verifies the decoded signed payload, not the raw wire
  bytes. `[V]`

#### 1.6 Webhooks received

| Webhook | Verification |
|---|---|
| **Polar** (billing) | HMAC-SHA256 verified before any processing. Both Standard Webhooks headers and the `polar-signature` form are accepted. |
| **Slack events** | Signing-secret validation. Bot tokens are stored encrypted. |

#### 1.7 Email

- **Sub-processor:** Brevo (Sendinblue GmbH, **DE**).
- **Email types:** invitation, invitation declined, two-factor
  recovery, password reset, verification, and data-export-ready
  notice.
- **PII redaction in logs:** an email address renders as a short
  SHA-256 prefix, never as plaintext. `[V]`

### 2. Data stored

#### 2.1 Postgres

| Table | Stored | Mutable? | Encryption at rest | Retention |
|---|---|---|---|---|
| `audit_events` | Organization, actor, action, event type, decision, policy id, policy version, policy hash, matched rule, reason code, `execution_id`, `action_digest`, tool name and version, metadata, content hash, previous hash, timestamp | **Immutable** | Database level | Until the organization purge, after a 60-day grace |
| `execution_records` | One row per execution, joined on `execution_id` | Mutable | Database level | The plan's history window |
| `cost_events` | Cost in cents and millicents, token counts, provider-reported and authoritative cost, an integrity label, tool and model, correlation ids, agent and organization ids, receipt timestamp. Partitioned by month. | Mutable | Database level | The plan's history window |
| `approvals` | The decision, and who made it — a person, a system expiry, or an unknown source | Mutable: pending becomes approved, denied, expired, or revoked | Database level | Pending rows are collected by a sweep worker |
| `organizations` | Id, name, slug, contact email, plan, deletion timestamp, purge date | Mutable, soft delete | Database level | Hard-deleted by the retention worker after the grace |
| `users` | Id, email, display name, password hash (Argon2id), role, default organization, tombstone timestamp | Mutable | Database level | Until the organization cascade |
| `organization_api_keys` | Id, name, key prefix and suffix, the key hash (Argon2id), the SHA-256 lookup fingerprint, the HMAC signing secret, status, version, last use, expiry, scopes | Mutable | Database level | Until the organization cascade |
| `user_2fa` | The user id, the TOTP secret, the pending TOTP secret, and the hashed recovery codes | Mutable | Column-level encryption on the TOTP secrets | Until the user row is deleted |
| `policies` | Id, scope, policy type, enforcement mode, budget amount, overdraft cap | Mutable, soft delete | Database level | The plan's history window |
| `approval_rules` | The typed predicates that ask for a human, mirroring the policy quota | Mutable | Database level | The plan's history window |
| `workflows` | Metadata, state (normal, flagged, tripped, paused, killed), budget amount, archive and deletion timestamps | Mutable | Database level | Persistent |

**Sessions are not in Postgres.** Browser sessions live in Redis under a
7-day expiry, and hold the user id, the organization id, and the creation
time. The token itself is the key. A revocation writes a tombstone.

#### 2.2 Immutability of the audit table

Four independent controls protect the audit table:

1. Row-level triggers refuse an update and a delete.
2. A schema-level event trigger refuses schema changes to the audit
   and audit-export tables.
3. Delete and truncate are revoked from the application role on the
   audit-export tables.
4. The triggers are armed so that a session-level replication-role
   change cannot disable them.

#### 2.3 Column-level encryption

Column-level encryption uses pgcrypto AES. It is applied to the Slack
OAuth bot tokens, the TOTP secrets, and the MCP discovery bearer
tokens. The threat model: a stolen disk image or a read-only dump
yields ciphertext, and the plaintext needs both the database and the
encryption key.

#### 2.4 Redis

Redis holds short-lived operational state. Grouped by purpose:

| Purpose | Contents | PII |
|---|---|---|
| Budget | The period cost counter, the reserved amount per execution | No |
| Execution binding | The organization and API key an `execution_id` belongs to | No |
| Rate limiting | Per-organization and per-key counters | No |
| Session and token | Session lookups and revocation tombstones, two-factor challenge and recovery tokens | User and organization id only |
| Chain state | The chain state machine for a chain of workflows | No |
| Audit chain fast path | The last event's content hash per organization | No |
| Circuit state | The workflow circuit-breaker state | No |

The keys hold opaque identifiers. The only personal data is the user
and organization id in the session entry.

### 3. Hosting

| Layer | Provider or location |
|---|---|
| **Cloud** | DigitalOcean LLC, US with EU regions. One VPS hosts the whole deployment. |
| **Postgres** | Self-hosted container on the VPS, with a dedicated application role and the pgcrypto extension. |
| **Redis** | Self-hosted container on the same VPS, with AOF and RDB backups. |
| **Object storage** | S3-compatible, for audit exports and backups. Compatible with DigitalOcean Spaces. |
| **Orchestration** | Docker Compose on one VPS. Blue-green deploys on the budget, billing, and gate paths; rolling deploys elsewhere. |
| **Edge** | No CDN. nginx on the VPS terminates TLS and reverse-proxies. The origin is directly reachable. |
| **DNS** | nginx virtual hosts for the marketing site and the API host. |

#### Container hardening

- Read-only root filesystem.
- All Linux capabilities dropped.
- No privilege escalation.
- A tmpfs for temporary files, mounted noexec, nosuid, and nodev.

#### TLS

- TLS 1.2 and 1.3 only.
- A Mozilla "intermediate" cipher list.
- HSTS with a one-year max age and subdomain inclusion.
- Certificates managed by Certbot. `[V]`

### 4. Access controls

#### 4.1 Roles

| Role | Level | Used for |
|---|---|---|
| Viewer | 0 | Read-only access. |
| Operator | 1 | Operator-tier mutations: kill and pause workflows, decide approvals. This level exists only at runtime. |
| Admin | 2 | Organization and member management. |
| Owner | 3 | Organization deletion, billing changes, ownership transfer. |

The storage layer has a parallel hierarchy: viewer, member, admin,
owner.

**Machine API keys carry no user role.** A mutation that the role
model protects needs a user-bound key.

**Platform admin** additionally needs two-factor enabled and the owner
role. A lookup failure refuses the request.

#### 4.2 Authentication

| Method | Wire |
|---|---|
| Session cookie (browser) | A host-prefixed cookie in production, HttpOnly, SameSite=Lax, 7-day lifetime. It fails closed to production rather than to development. |
| API key (machine) | A prefixed key; the request body is signed with HMAC-SHA256 over the timestamp, the key, and a hash of the body. Rotation is versioned and fans out to every instance. The comparison is constant-time. |
| OAuth (identity) | GitHub and Google. |
| SSO | SAML and OIDC single sign-on. |

#### 4.3 Two-factor

- TOTP with six digits, a 30-second period, and ten recovery codes on
  enable.
- Platform-admin endpoints need a two-factor-enabled user.
- Recovery tokens for OAuth users disabling two-factor are
  single-use, hold a user id, and expire after 24 hours. `[V]`

#### 4.4 API key scopes

- An admin scope is required for non-owner admins on admin paths.
- A key carries its workflow id. A body `workflow_id` that does not
  match the key is refused with `WORKFLOW_ID_BODY_MISMATCH`.
- Status: active, rotating, or revoked.

#### 4.5 Audit log access

- **Plan-gated.** A plan feature flag controls read access. Plans
  without the flag give the customer no access.
- **Database policy.** A per-organization row policy exists on the
  audit table, and a raw reader must set the current-organization
  context. The deployed application role is a superuser with row-level
  security bypassed, so the policy does not bind there. Tenant scoping
  in production comes from the queries, not from the policy.
- **Retention.** The plan's history window controls customer-visible
  history. A value of -1 means unlimited.

#### 4.6 Operator access to production

- Shell access goes through an allowlisted wrapper that permits a
  small set of read-only commands.
- Blocked: environment dumps, container inspection, reading the
  production environment file, and every mutating container command.
- Production credentials come from a CI secret and are rendered
  atomically.

### 5. Encryption

| Layer | Mechanism | Attestation |
|---|---|---|
| **In transit, server edge** | TLS 1.2 and 1.3, Mozilla intermediate ciphers, HSTS | `[V]` |
| **In transit, WebSocket** | HMAC-SHA256 over canonical JSON, 300-second replay window | `[V]` |
| **At rest, Postgres columns** | pgcrypto AES, hex-encoded, on the Slack OAuth bot tokens, the TOTP secrets, and the MCP discovery bearer tokens | `[V]` |
| **At rest, Postgres disk** | **Not attested**; relies on the provider's disk encryption | `[N]` |
| **At rest, Redis** | **Not attested**; the backup volumes rely on host disk encryption | `[N]` |
| **At rest, object storage** | S3-compatible storage. Bucket-side encryption settings are **not exposed** | `[D]` |
| **Key management** | One environment-held key drives the column encryption. No managed key service is integrated. Rotation needs a manual runbook, and it breaks two-factor and Slack until every copy is replaced | `[D]` |
| **Request signing** | HMAC-SHA256 over gate, execute, and track bodies. The signing key is at least 32 bytes and is never generated automatically | `[V]` |
| **API keys at rest** | The key itself is stored as an Argon2id hash. A SHA-256 fingerprint of the key is stored beside it, so the row can be found without a full hash verification. The signing secret is stored in plaintext because the hot path needs it. A prefix and suffix are kept for display | `[V]` |
| **Cookies** | Host prefix, Secure, HttpOnly for the session, SameSite=Lax, Path=/, 7-day lifetime. The CSRF cookie is readable by the single-page app by design | `[V]` |
| **Audit exports** | An HMAC-SHA256 sidecar signature, keyed by one deployment-wide secret held in the environment. The secret is required in production: with it unset and no explicit development, test, or staging environment set, the service refuses to start. A fixed development value is used only in those explicit non-production environments | `[V]` |

### 6. Sub-processors

The canonical list is served from a public endpoint and cached with an
entity tag.

| Sub-processor | Role | Country | Transfer mechanism | Opt-in |
|---|---|---|---|---|
| **DigitalOcean LLC** | Hosting: Postgres, Redis, application servers | US, with EU regions | EU standard contractual clauses for the US region | No |
| **Brevo (Sendinblue GmbH)** | Transactional email | DE | EU adequacy decision | No |
| **Polar.sh (Polar Software Sweden AB)** | Payment, subscription, tax, merchant of record | SE | EU adequacy decision | No |
| **Slack Technologies, LLC** | Alert delivery and OAuth | US | EU standard contractual clauses | Yes |
| **GitHub Inc.** | OAuth identity provider | US | EU standard contractual clauses | Yes |
| **Google LLC** | OAuth identity provider | US | EU standard contractual clauses | Yes |

**Model providers.** NULLRUN does not proxy calls to OpenAI,
Anthropic, Google, or Azure. The SDK talks to providers directly with
the customer's own keys.

**Analytics and observability.** Self-hosted: Prometheus, Grafana,
Alertmanager, Vector, and Loki. No third-party analytics vendor.

**Backup storage.** S3-compatible, with the configuration archive
encrypted before upload.

### 7. Deletion

#### 7.1 Organization deletion

**Soft-delete.** The organization row is marked deleted and a purge
date is set 60 days out. Audit rows stay for the grace period because
the audit chain must stay intact. An owner can restore the
organization, which clears both markers. A delete request that would
leave audit history behind is refused with a `409` that names the
grace period and its length. Child records — keys, policies,
workflows, invitations — are updated in the same transaction.

**Hard purge.** The purge runs after the purge date. It scrubs the
audit log, the decision history, the cost events, and the billing
events, then deletes the organization row. The update and delete
triggers on the audit table are disabled inside that transaction and
re-armed afterwards, so they cannot be bypassed by a session-level
setting.

#### 7.2 User account deletion

Three cases:

| Case | Behaviour |
|---|---|
| The only owner of the only member's organization | The organization is soft-deleted. No decision is required. |
| Co-member organization, the user chooses delete and notify | Soft delete, and every co-member session is revoked. A revocation failure refuses the request. |
| Co-member organization, the user chooses transfer | A new owner is promoted and nothing is deleted. |

The request carries an ownership-decisions map keyed by user id. A
session-revocation failure refuses the request. `[V]`

#### 7.3 API key revocation

Three phases:

1. The key moves to rotating, every instance is notified, and a deny
   list short-circuits warm-cache hits.
2. A drain supervisor waits for the in-flight counter to reach zero,
   or for the timeout to expire.
3. The key becomes revoked. The counter is preserved for audit and
   reconciliation.

The deny list lives for twice the authentication cache lifetime.

#### 7.4 GDPR

| Right | Implementation |
|---|---|
| **Access** | A per-user export job. The download expires after 7 days, and each section is capped at 100 000 records. The session section reads a Postgres table that the migrations do not create, so it comes back empty and the job logs it and continues. |
| **Erasure** | The tenant purge scrubs tenant-scoped data, and runs automatically 60 days after the soft delete. There is no self-serve kickoff path. |
| **Audit retention on erasure** | Audit rows are physically deleted when the organization is purged. They are retained through the grace period on purpose. |
| **Drift guard** | An automated check keeps personal data from accumulating in payloads where it would later need to be scrubbed. |

### 8. Data residency

- **Physical storage:** DigitalOcean. The region is selectable at
  signup, and a customer who picks EU gets EU-resident Postgres and
  Redis.
- **Cross-region replication:** **Not attested**. The deployment is
  single-region.
- **Cross-border transfers:**
  - US sub-processors — DigitalOcean US, Slack, GitHub, Google — use
    EU standard contractual clauses, modules 2 and 3.
  - EU sub-processors — Brevo in DE, Polar in SE, DigitalOcean EU —
    rely on the EU adequacy decision.
- **Region enforcement:** the region chosen at signup decides where the
  data physically sits. The signup mechanism is not exposed on the
  wire. `[D]`

### 9. Compliance posture

| Item | Status | Attestation |
|---|---|---|
| **Data processing agreement** | Available. The org endpoint returns the accepted version and its history. Acceptance is idempotent per version and is recorded as an audit row. | `[V]` |
| **Sub-processor list** | Served from a public endpoint, cached with an entity tag. | `[V]` |
| **GDPR access** | Per-user export implemented. | `[V]` |
| **GDPR erasure** | Right to erasure through the tenant purge, after a 60-day grace. | `[V]` |
| **SOC 2** | The audit-table immutability guarantee is the control surface. **No SOC 2 Type II report is available.** | `[D]` |
| **ISO 27001** | **Not claimed** | `[N]` |
| **HIPAA** | **Not claimed** | `[N]` |
| **CCPA** | **Not claimed** | `[N]` |
| **Audit export** | HMAC-signed JSONL or an object-storage download, produced by a background worker. | `[V]` |

### 10. Breach and incident response

| Item | Status | Attestation |
|---|---|---|
| **Alerting surface** | A self-hosted Prometheus Alertmanager plus Slack, with per-channel OAuth. Rules cover the cost-tracking error rate, latency percentiles, out-of-order events, and similar. PagerDuty is not supported. | `[V]` |
| **Alert channels** | Webhook and Slack. Email, PagerDuty, and Discord are not supported. | `[V]` |
| **Runbooks** | Topic-specific runbooks exist for the cost-tracking error rate, a stuck audit drain, a stuck outbox, a period rollover, a credential leak, and billing drift. | `[V]` |
| **Status page** | **Not referenced** | `[N]` |
| **Breach-notification SLA** | **Not documented** | `[N]` |
| **On-call rotation** | **Not documented** | `[N]` |

### 11. Penetration testing

| Item | Status |
|---|---|
| **Internal pentest** | A phased pentest profile exists, executed against a local Docker stack. |
| **Findings fixed in code** | Trigger hardening closed an audit-table immutability bypass that a session-level replication-role change could have opened. |
| **External pentest report** | **Not available** |
| **Bug bounty program** | **Not advertised** |

### 12. Other load-bearing controls

- **Signed gate calls.** Signature verification is mandatory in
  production. A missing or invalid signature is refused before
  enforcement runs.
- **Protocol header required.** Every gate request carries a protocol
  version header. The service publishes the minimum and maximum it
  accepts.
- **Fail-closed on enforcement paths.** When the budget store is
  unreachable the gate answers `402` with
  `BUDGET_REDIS_UNAVAILABLE`. It never answers "allow" without a
  budget answer.
- **Cross-tenant guards.** Body organization mismatch, workflow-id
  mismatch between the body and the key, and a parent execution from
  another organization are each refused.
- **CSRF double-submit** on browser POSTs, with a bearer-token
  exemption for API paths. The comparison hashes first and compares in
  constant time.
- **PII redaction** in log lines.
- **Secret scanning before commit.** Two scanners, one general and one
  for NULLRUN key shapes, plus a file-size limit.

### Honest gaps

These are the questions a vendor reviewer should follow up on.

#### Not attested `[N]`

1. **Formal attestations.** No SOC 2, ISO 27001, HIPAA, or CCPA
   certificate or report exists. The immutability wording describes a
   self-imposed control, not a third-party certification.
2. **External penetration test report.** Only an internal plan and
   journal exist.
3. **Bug bounty program.** Not advertised.
4. **Status page.** No public status host is referenced.
5. **Breach-notification SLA.** Not documented.
6. **Disk-level encryption at rest.** Column-level encryption covers
   the Slack OAuth bot tokens, the TOTP secrets, and the MCP discovery
   bearer tokens. Full-disk or tablespace encryption relies on the
   provider's disk encryption.
7. **Redis disk encryption.** The backup volumes are bind-mounted
   with no documented encryption at rest.
8. **Object-storage encryption settings.** Bucket-side encryption
   configuration is not exposed.
9. **Customer-side region selection.** The agreement refers to a
   signup-time choice, and the wire path that records it is not
   exposed.
10. **Cross-region replication and disaster recovery.** The deployed
    topology is one region on one VPS. No failover is documented.
11. **Privacy policy page.** Not published on the site.

#### Derived, not directly attested `[D]`

12. **Managed key service.** The encryption key is an environment
    value with no managed key service behind it, and rotation needs a
    manual runbook.
13. **Operator action logging.** The production shell path is
    allowlisted, and the product writes its own audit rows. There is
    no separate record of operator actions at the database tier.
14. **Granular API key scopes.** An admin scope is the only named
    scope. Per-workspace or per-operation scopes are not enumerated.
15. **Client-side TLS minimum.** TLS 1.2 and 1.3 are enforced at the
    nginx edge. Whether the SDK pins a minimum version was not
    audited.

### See also

- [Compliance overview](#81-overview)
- [Performance & limits](#92-performance-limits) — timeouts and
  the fail-closed posture
- [API keys](#25-api-keys) — signing, rotation, revocation
- [Organization](#56-organization) — the delete-organization
  flow
- [Profile settings](#57-profile-settings) — the delete-account flow


# 9. Operations


## 9.1 Troubleshooting

Format: symptom → cause → fix. If your case is not here, see the
[Errors reference](#75-error-codes), or send a report from the
control center's **Help → Send feedback** form with the `workflow_id` and
the failing decision id.

!!! info "The endpoints that enforce"
    The server answers `410 Gone` on `POST /api/v1/check`, so a client
    that calls `/check` never reaches enforcement. The SDK calls
    **`POST /api/v1/gate`** for the budget and **`POST /api/v1/execute`**
    for the tool policy. Both refuse the call when a rule says no.

### The gate refused the call

Every row below is a decision the gateway made. The wire code is in
the response body, and the SDK raises the exception in the last
column.

| Symptom | Wire code | Status | SDK exception | Fix |
|---|---|---|---|---|
| The workflow ran out of budget | `BUDGET_HARD_BLOCKED` | `402` | `NullRunBudgetError` | Raise the budget in the control center, or wait for the next billing period. |
| The organization's ceiling was reached | `BUDGET_ORG_CEILING_BLOCKED` | `402` | `NullRunBudgetError` | Raise the plan ceiling, or lower the workflow budgets under it. |
| The call cost more than its reservation | `CONSUME_OVERBUDGET` | `422` | `NullRunConsumeOverbudgetError` | Report the real cost. A cost above the reservation plus the tolerance is refused. |
| A tool matches a block pattern | `TOOL_BLOCKED` | `403` | `NullRunToolBlockedError` | Change the pattern, or use a different tool. |
| An MCP tool is destructive | `MCP_DESTRUCTIVE_BLOCKED` | `403` | `NullRunMcpDestructiveBlockedError` | The tool is off limits for this workflow. |
| The plan's executions quota is spent | `EXECUTION_QUOTA_EXCEEDED` | `402` | `NullRunBlockedException` | Raise the plan, or wait for the quota to reset. |
| The workflow is not running | `WORKFLOW_INACTIVE` | `403` | `NullRunWorkflowInactiveError` | Restore the workflow in the control center, or create a new one. |
| The workflow is paused | `WORKFLOW_PAUSED` | `403` | `NullRunBlockedException` | Resume it in the control center. |
| A policy rate limit was hit | `RATE_LIMIT_EXCEEDED` | `429` | `RateLimitError` | Back off. The window is fixed, not sliding. |
| The plan's aggregate cap was hit | `RATE_LIMIT_PLAN_TIER` | `429` | `RateLimitError` | Raise the plan. The cap belongs to the plan, not to your policy. |
| Too many approvals are waiting | `TOO_MANY_PENDING_APPROVALS` | `429` | `NullRunBlockedException` | Clear the backlog in the Approvals view. The cap is 50 per organization. |
| The chain ran past its duration | `CHAIN_MAX_DURATION_EXCEEDED` | `402` | `NullRunChainError` | Start a new chain. The gateway ends a chain after one hour. |
| The request used a stale protocol version | `PROTOCOL_TOO_OLD` | `400` | `NullRunProtocolError` | Upgrade the SDK. It sends version 4. |
| The key is revoked, expired, or disabled | `API_KEY_REVOKED`, `API_KEY_EXPIRED`, `API_KEY_INVALID` | `401` | `NullRunAuthError` | Rotate the key in the control center. |

#### The refusal is the wrong one

**The tool name does not match the pattern you wrote.** Matching is
case-sensitive and reads the tool name only. A pattern of
`stripe.*` matches `stripe` and `stripe.charge`, and it does not
match `stripe_charge`. Use `stripe*`. See
[Tool catalog → Pattern syntax](#76-tool-catalog).

**The approval says the digest does not match.** The approval is bound
to the exact payload it approved. If the arguments changed, the
binding is broken, and the call is refused with
`APPROVAL_DIGEST_MISMATCH`. Send the payload that was approved.

**The approval says the tool does not match.** An approval covers the
tools it was granted for. Running a different tool under that grant is
refused with `APPROVAL_TOOL_MISMATCH`.

### The gateway cannot be reached

Two different failures look alike from the outside. The distinction
matters, because one is a transport fault and the other is a policy
refusal.

| Symptom | Cause | SDK exception | Fix |
|---|---|---|---|
| `NullRunTransportError` right after `init()` | The gateway did not answer the authentication handshake (`POST /api/v1/auth/verify`). | `NullRunTransportError` (NR-B001) | Check the gateway URL and the network. |
| `NullRunBackendError` with a `5xx` status | The gateway answered and reported a fault. | `NullRunBackendError` (NR-B002) | Read the wire code in `details.error_code` and follow its runbook. |
| `NullRunRateLimitRedisError` | The aggregate per-organization rate limiter could not read its counter. The refusal is `503` `RATE_LIMIT_REDIS_UNAVAILABLE`. | `NullRunRateLimitRedisError` (NR-R002) | Back off and retry with jitter. |
| `NullRunBudgetError` with a `402` and `BUDGET_REDIS_UNAVAILABLE` | The budget store was unreachable. The refusal is fail-closed. | `NullRunBudgetError` | Wait for the store to recover. Do not retry the side effect blindly. |
| `NullRunAuthenticationError` or `NullRunAuthError` | The key is missing, rejected, expired, or disabled. | `NullRunAuthenticationError` (NR-A001), `NullRunAuthError` (NR-A003) | See the authentication section. |
| `BreakerTransportError` during a run | The SDK's circuit breaker is open. It watches the event flush, not the gate, and opens after 10 consecutive failed flushes. | `BreakerTransportError` | Wait 30 seconds, then check the gateway. Pending events stay on disk. |

The circuit breaker is the one component that fails open. It fails open
locally: an unreachable gateway short-circuits the event flush inside
your process instead of hanging. The enforcement path itself never
fails open. A missing tool-block answer, a missing rate-limit answer,
or a missing budget answer refuses the call. See
[Circuit breaker](#21-circuit-breaker).

#### Do not disable the gate to survive an outage

`NULLRUN_SKIP_BUDGET_CHECK` and `NULLRUN_SENSITIVE_FAIL_OPEN` are
development opt-outs. Each one also needs a second opt-in, and the
sensitive-tool set is empty by default. Neither belongs in a
production deployment. Catch the exception and retry in your code.

### The approval never arrives

| Symptom | Cause | SDK exception | Fix |
|---|---|---|---|
| The wait ended with nothing decided | Nobody answered inside the approval window. The default is 300 seconds, and the SDK clamps the value to between 1 and 3600 seconds. | `NullRunApprovalExpiredError` (NR-A012) | Raise the timeout, or ask a human to answer sooner. |
| The approval was declined | An operator said no. | `NullRunApprovalDeniedError` (NR-A011) | The refusal is final for that payload. Do not retry it. |
| The approval is still pending | The decision has not been made yet. | `NullRunApprovalNotYetApprovedError` (NR-A010) | Wait, or ask the operator. |
| The grant was already used | The same approval was presented twice. | `NullRunApprovalReplayRejectedError` (NR-A015) | Request a fresh approval. |

The approval wait is bounded by
`NULLRUN_APPROVAL_TIMEOUT_SECONDS`. A pending approval stays on the
server through a gateway outage, so it reappears in the Approvals view
once the gateway recovers.

### The call is rejected with `NullRunBlockedException`

The base class covers every refusal that has no more specific class.
Read `exc.status_code` and `exc.details` to find the reason, then
match the wire code against the
[gate refusal table](#the-gate-refused-the-call).

One extra pointer: the workflow's detail page lists the merged
policies in scope, so a tool block can be traced to the rule that
produced it. See [Workflow context](#41-workflow-context) for the
workflow states a refusal can name.

### The workflow paused or killed on its own

- **An operator acted.** The workflow's audit log shows the actor and
  the timestamp.
- **A plan cap was reached.** The plan limits the number of live
  workflows. The per-tier table is in
  [Performance & limits → Per-plan limits](#92-performance-limits).

### The SDK raises `NullRunAuthenticationError`

- `NULLRUN_API_KEY` is unset or empty. `init()` reports this with
  error code `NR-C001`.
- The key was revoked, expired, or disabled. The gateway answers `401`
  with the specific code, and the SDK raises `NullRunAuthError`.
- The host clock is too far from the gateway's clock for the signed
  request window. Sync the clock.
- The protocol version is outside the range the gateway supports. The
  SDK sends version 4, and a gateway that answers `PROTOCOL_TOO_OLD`
  does not accept it.

### The SDK raises `ValueError` for the chain id

A chain id must be a UUID v4. The SDK validates the format, the
canonical structure, and the version, and rejects anything else with
a `ValueError`. The `chain()` context manager also takes an
operation, and the valid values are `start`, `continue`, `end`, and
`auto`.

```python
import uuid

import nullrun

with nullrun.chain(str(uuid.uuid4()), op="start"):
    ...
```

### Some calls are tracked and others are not

`@protect` fires on the functions it wraps. A plain model call with
no `@protect` and no auto-instrumented framework is invisible to
NullRun. The SDK instruments these clients on its own, so a model call
made through one of them is tracked without a decorator: `httpx`,
`requests`, LangChain, LangGraph, the OpenAI Agents SDK, LlamaIndex,
CrewAI and AutoGen. See [LLM frameworks](#65-llm-frameworks).

### Health endpoints

| Endpoint | Purpose |
|---|---|
| `GET /health/live` | Process liveness. It answers 200 while the binary runs, even when a dependency is down. Do not use it as a readiness signal. |
| `GET /health/ready` | Dependency readiness. It answers 503 when the database or the budget store is unreachable. This is the signal to page on. |
| `GET /health/startup` | Bootstrap readiness. It answers `started` once migrations and seeds are done. |
| `GET /api/v1/capabilities` | The protocol version range, the live feature flags, and the server version. |

During an outage, `/health/ready` flips first, then the capability
probe answers, then the control-plane WebSocket reconnects, then the
cost-event outbox finishes draining.

### See also

- [Errors reference](#75-error-codes) — the exception hierarchy
- [Circuit breaker](#21-circuit-breaker)
- [Control plane](#44-control-plane-websocket)
- [Budgets](#31-budgets)
- [HTTP API](#73-http-api)


## 9.2 Performance & limits

The bounds a NullRun integration runs inside. Every number here is
enforced in code, not a target.

### Timeouts

| Bound | Value | Set by |
| --- | --- | --- |
| One gateway request | **30 s** | The SDK, via `NULLRUN_REQUEST_TIMEOUT` |
| Gate handler | **5 s** | The gateway |
| Gate evaluation | **3 s** | The gateway |
| Waiting for an approval | **300 s** by default, between 1 s and 3 600 s | The SDK, via `NULLRUN_APPROVAL_TIMEOUT_SECONDS`, clamped |
| A reservation lives for | **300 s** by default. An approval rule with a deadline extends it to that deadline plus 30 s, and the ceiling is 24 h. | The gateway |

The 3 s evaluation cap is the binding one. The 5 s handler cap is a
safety net above it, and the 30 s request cap is the outermost bound.

Two consequences worth planning around:

- A tool call that runs longer than the reservation lifetime loses
  its reservation. The cost that follows is refused, so budget the
  tool's runtime against the reservation, not against the budget.
- An approval that no human answers inside the window fails. The
  exception is `NullRunApprovalExpiredError`.

### Retries

The SDK retries failed calls. The gateway does not retry for the
caller.

| Call | Retries | Backoff |
| --- | --- | --- |
| Gate | **3** | 0.5 s base, doubled each attempt, capped at 10 s, with jitter |
| Execute | **10** | 0.5 s base, doubled each attempt, capped at 30 s, with jitter |
| Event flush batch | **10** | 0.5 s base, doubled each attempt, capped at 10 s, with jitter |

A `4xx` answer is a decision and is never retried. A `Retry-After`
value replaces the computed delay and is treated as a floor, so the
retry never lands before the server permits it.

### Rate limits

#### By address and account

| Limit | Value | Response |
| --- | --- | --- |
| Per IP address | **60 requests per minute**, burst 60 | `429` with `Retry-After` |
| Auth endpoints, per IP | **5 attempts per minute** | `429` |
| One email address | **5 consecutive failures** → 300 s lockout | `429` with `Retry-After` |

#### By policy

| Limit | Value | Response |
| --- | --- | --- |
| Per organization and API key | The rate-limit policy's `limit`, counted over the policy's own window. A fixed window, not a sliding one. | `429` `RATE_LIMIT_EXCEEDED` |
| Per organization | The plan's aggregate cap, in requests per minute | `429` `RATE_LIMIT_PLAN_TIER` |

An explicit `RateLimit` policy wins over the plan tier. A policy that
asks for more than the plan allows is clamped down to the plan's cap,
and the clamp is reported in `details.clamped_from_rpm`.

#### The plan's aggregate cap

| Plan | Requests per minute, per organization |
| --- | --- |
| Lite | 10 000 |
| Starter | 50 000 |
| Growth | 200 000 |
| Scale | 1 000 000 |
| Enterprise | unlimited |

### Per-plan limits

| Plan | Workflows | Tokens per hour | Executions per month | Requests per second | API keys | Seats | Policies |
|---|---|---|---|---|---|---|---|
| **Lite** | 3 | 10 000 | 75 000 | 5 | 10 | 1 | 3 |
| **Starter** | 8 | 25 000 | 100 000 | 10 | 15 | 3 | 10 |
| **Growth** | 50 | 300 000 | 750 000 | 50 | 100 | 10 | 25 |
| **Scale** | 200 | unlimited | 2 000 000 | 300 | 350 | 75 | 150 |
| **Enterprise** | unlimited | unlimited | unlimited | unlimited | unlimited | unlimited | unlimited |

Approval rules need a plan that includes approvals. Lite and Starter
do not include it, so the create call is refused with `403`
`feature_not_available`. Every other plan carries an approval-rule
quota alongside its policy quota.

### When the gateway is unreachable

The SDK ships a circuit breaker in front of the event flush. It is the
one component in the chain that fails open, and it fails open locally:
the flush is short-circuited inside your process, so a gateway outage
does not turn into a hang. The breaker does not sit on the gate path.

| Setting | Value |
| --- | --- |
| Consecutive failed flushes before the breaker opens | **10** |
| How long the breaker stays open | **30 s** |
| Probe calls allowed while half-open | **1** |

A flush that the breaker short-circuits raises
`BreakerTransportError`. A call that reaches the gateway and gets a
refusal raises the refusal's own exception. The two are different
outcomes and only one of them is a policy decision.

The enforcement path itself never fails open. Every signal below is
required, and a missing signal refuses the call.

| Missing signal | Response |
| --- | --- |
| The tool-block answer | `403` `TOOL_BLOCKED` |
| The aggregate rate-limit answer | `503` `RATE_LIMIT_REDIS_UNAVAILABLE` |
| The budget answer | `402` `BUDGET_REDIS_UNAVAILABLE` |
| The protocol header | `400` `PROTOCOL_HEADER_REQUIRED` |
| The state store, on the cost-tracking path | `200`, retried in the background |

The last row is the only exception. The cost event is written after
the inference has already happened, so the gateway acknowledges the
call and retries the write. The spend is not lost.

### What a refusal looks like

| Situation | Status | Code |
| --- | --- | --- |
| The workflow's budget is exhausted | `402` | `BUDGET_HARD_BLOCKED` |
| The organization's ceiling is reached | `402` | `BUDGET_ORG_CEILING_BLOCKED` |
| The call costs more than its reservation | `422` | `CONSUME_OVERBUDGET` |
| A tool matches a block pattern | `403` | `TOOL_BLOCKED` |
| A policy's rate limit is hit | `429` | `RATE_LIMIT_EXCEEDED` |
| The plan's aggregate cap is hit | `429` | `RATE_LIMIT_PLAN_TIER` |
| Too many approvals are waiting | `429` | `TOO_MANY_PENDING_APPROVALS` |
| The workflow was paused from the control center | `403` | `WORKFLOW_PAUSED` |

A consume may exceed its reservation by a small fixed tolerance —
1¢ by default. A larger overshoot is refused with
`CONSUME_OVERBUDGET`.

The per-organization pending-approval cap is **50** by default. A 51st
waiting approval is refused with `TOO_MANY_PENDING_APPROVALS`, and the
caller gets a `429`.

### Gaps

The things we have not measured, stated plainly.

#### Not measured

- Real p99 latency to the budget store at production scale, on the
  worst-case reservation path.
- First-request latency during a budget-store partition, before the
  gateway's own breaker trips.
- Write throughput for the cost-event store under a tracking burst.
- Reconnect behaviour for the control-plane WebSocket under a
  split-brain. The gateway puts no cap on it.

#### Known limits

- The audit drain retries on a fixed 1, 2, 4, 8, 16 second schedule.
  The delivery outbox retries 30 s doubled each attempt, with jitter.
- `Retry-After` on the gate path is a body field (`retry_after_seconds`
  and `retry_after_ms`). The gate does not set the HTTP header. The
  per-IP limiter and the generic error envelope do.
- The published OpenAPI contract carries fewer response fields than
  the gateway returns. The running gateway is the wire truth.

### See also

- [Circuit breaker](#21-circuit-breaker) — what the agent
  sees when a failure occurs
- [Error handling](#43-error-handling) — wire code to
  exception mapping
- [Budgets](#31-budgets) — reserve and consume semantics
- [API keys](#25-api-keys) — signing, rotation, drain
- [Control plane](#44-control-plane-websocket) — WebSocket keepalive
- [HTTP API](#73-http-api) — endpoints and the protocol
  version
- [Compliance](#81-overview) — data-handling posture


## 9.3 Framework & ecosystem positioning

Teams that already run an agent framework ask two questions: what
does NullRun add, and where does it collide with what I have.

This page answers both. The short version: the framework owns **flow
control**, NullRun owns **authorization**. One of them — approval for a
sensitive tool — is a real overlap.

### The layers

Two layers belong to the framework:

- **Flow control.** Graph state, node order, scheduling.
- **Flow-level HITL.** Pausing a step and waiting for input.

NullRun does not manage graph state, and it does not decide whether the
agent's plan is a good plan.

Four layers belong to NullRun. The gateway enforces all of them.

| Layer | What it does |
|---|---|
| **Hard budget gate** | Reserves the cost of a call before it runs, against a period-bound counter. A refusal stops the call. |
| **Tool-call policy** | A declarative list of block and allow patterns, matched on the tool name. |
| **Immutable audit trail** | A hash-chained log of gate decisions, kept separate from execution records. A refusal is in it. |
| **Policy as data** | Scopes and versions in the control center, per organization and per workflow. |

NullRun sits above the framework layer. It does not replace it.

### What the SDK instruments automatically

`nullrun.init()` installs the patches. There is no patch to install
and no opt-in list to maintain.

| Path | What the SDK patches | Gate check |
|---|---|---|
| `httpx` | The `httpx.Client` and `httpx.AsyncClient` transports | Before the request |
| `requests` | The `requests` session | Before the request |
| LangChain | `BaseCallbackManager` | On the model call |
| LangChain | `BaseChatModel.invoke`, `ainvoke`, `stream`, `astream` | On the model call |
| LangGraph | `Pregel.invoke`, `stream`, `ainvoke`, `astream` | On the model call |
| OpenAI Agents | `Runner.run`, `Runner.run_sync` | None |
| LlamaIndex | The `llama_index.core` dispatcher | None |
| CrewAI | `Crew.kickoff`, `Crew.kickoff_async`, and the event bus | None |
| AutoGen | `BaseChatAgent.on_messages` and the OpenAI model client | None |

Where there is no gate check, the SDK still records the call, so the
cost reaches the ledger. Put `@protect` on the tools that carry policy
weight.

### The one real overlap: action-level approval

Both layers can ask a human about the same sensitive tool. They ask
different questions, and the people who answer them are usually
different.

| Layer | Question | When it fires | Who answers |
|---|---|---|---|
| Framework HITL | "Is this step right?" | Inside a node, around the model or tool call | The flow's operator |
| NullRun approval | "Is this action allowed under this policy?" | Before the tool function body runs | The governance team, in the Approvals view |

Both can fire on one tool call. That is the design point, not a
conflict — a run can need both an operator who confirms the plan and a
governance team that authorizes the action.

#### Where it bites

**Latency.** Every protected call adds one round trip to the gateway.
For batch agents this is invisible. For a latency-sensitive chat UI it
may matter. Two ways to reduce it:

- Protect only the calls that carry policy weight.
- Use the framework's own HITL for planning steps and NullRun
  approval for sensitive tool calls only.

**Two approval surfaces.** If both layers fire on the same tool, the
operator can see two prompts. One way out: use the framework's HITL for
planning and NullRun approval for sensitive invocations only.

**Conceptual confusion.** A team can have a complete framework HITL
setup and still overspend, still write to production without a
decision, and still have no enforcement log to show an auditor.

### Coexistence guidance

#### LangGraph and LangChain

Keep your own HITL nodes as they are. Add `@protect` on the tool
functions and on the model call site inside the node. `nullrun.init()`
installs the framework patches, so there is nothing to wire up.

#### CrewAI

Keep your own human-input step. It answers "is the framing right?".
Add `@protect` on tool calls that carry policy weight: database writes,
outbound email, payments. The CrewAI patch records the run's cost, so
`@protect` is what gates the calls.

#### AutoGen

Conversational HITL stays outside NullRun's scope. Wrap the agent
invocation site with `@protect`.

#### OpenAI Agents

Keep your run-level lifecycle hooks. Add `@protect` on the tool
function itself. The SDK instruments `Runner.run` and `Runner.run_sync`
automatically.

### What NullRun does not claim

These are outside the product by design, not gaps in the roadmap.

1. **Output moderation.** Content safety, PII redaction, prompt
   injection blocking. Use a model-side guardrail.
2. **Orchestration.** Graph state, DAG execution, and scheduling.
3. **Retrieval governance.** Vector store and retrieval quality.
4. **Network egress policy.** NullRun decides on call metadata. It
   does not inspect a tool payload for exfiltration.
5. **Provider-side cost reconciliation.** NullRun prices the tokens it
   records against its own pricing table. It does not compare that
   number with the provider's invoice.

If your evaluation includes one of these, NullRun is a complement.

### Gaps

- **Framework drift.** Framework HITL features move quickly. Check the
  vendor's current documentation for the framework you run.
- **No latency benchmark against framework HITL.** A framework pause is
  a process-local suspension. A NullRun decision is a network
  authorization call. The two numbers are not comparable, and NullRun's
  own p99 at production scale is not measured.
- **No empirical study of approval friction.** The mitigations above
  are design guidance. Teams running both layers should compare the
  two surfaces before committing.
- **No automatic link between a framework thread id and a NullRun
  `execution_id`.** The two ids have different shapes, and joining
  them is on the adopter.

### See also

- [Performance & limits](#92-performance-limits) — timeouts, rate limits, and
  the fail-closed posture
- [Protect a LangGraph agent](#61-protect-a-langgraph-agent)
- [Use with OpenAI Agents](#62-use-with-openai-agents)
- [Use CrewAI](#63-use-crewai)
- [LLM frameworks](#65-llm-frameworks)
- [Human approval](#32-human-approval)
- [Sensitive tools](#24-sensitive-tools)
- [Budgets](#31-budgets)


## 9.4 Changelog

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
    pip install nullrun==0.24.0
    ```

### 0.24.0 — 2026-11-08

The enforcement path stopped swallowing refusals. A gate that answered
"no" could be turned into `None`, and `None` is read by every caller as
"yes". A refused `/track` could be logged and returned as an ordinary
call. A LangChain callback dropped the refusal on the floor, so the
agent got the call for free.

The control plane got a second fix. The approval push read the unsigned
outer body — the bytes the HMAC never covered — and handed them to the
handler that releases a gate parked waiting for a human. The privileged
branch now requires an authenticated frame and reads the verified
payload only.

There is no wire-format change. Every new error code the SDK names is a
code the gateway already sends, and the one code that is new to both
repos, `APPROVAL_TOOL_MISMATCH` (HTTP 409), shipped together with its
gateway half.

#### Changed

- **`check_workflow_budget` lost its `use_gate_cache` parameter.**
  Passing it now raises `TypeError` — remove the argument. The
  in-process gate cache is gone. Every call is its own `/gate` call with
  its own reservation.

- **`NULLRUN_SENSITIVE_FAIL_OPEN` opens nothing on its own.** The
  switch is still a whole-system switch, but the tools it may open are
  now an explicit, code-level list. The list is empty by default, so
  the switch alone opens nothing and every tool stays fail-CLOSED.
  Four runtime methods drive it:

  ```python
  runtime.register_fail_open_tools(["charge_card"])
  runtime.remove_fail_open_tool("charge_card")
  runtime.get_fail_open_tools()
  runtime.is_fail_open_allowed("charge_card")
  ```

- **A gate refusal now escapes the LangChain / LangGraph callback.**
  The refusal is re-raised instead of being caught by a blanket
  `except Exception`. A cosmetic failure is still swallowed at DEBUG —
  only a refusal escapes.

- **An indeterminate gate decision is a refusal, not a permission.**
  When the SDK's own code faults while asking the gateway, the SDK
  raises `NullRunGateIndeterminateError` (NR-P004) instead of returning
  "no decision, carry on".

- **The write-ahead log path changed.** The default is now
  `<tempdir>/nullrun-<user>-<key>.wal`. Both scope tokens are SHA-256
  digests, so the API key never reaches a path every user on the host
  can list. `NULLRUN_WAL_PATH` still wins outright.

- **`api_key_prefix` renders as a fingerprint.** The public field keeps
  its name; the value is the first eight hex characters of the SHA-256
  digest of the key. The log label is `api_key_fp=`. Log parsers that
  matched the old raw prefix must change.

- **The MCP tool-annotation cache window is 30 seconds.** A failed
  refresh no longer presents the previous snapshot to the gateway — the
  gateway gets the unknown shape the adapter uses for a tool it has
  never seen, and falls back to its own classifier. Pass
  `cache_seconds=0` for no staleness at all.

- **Three new public exceptions.**
  `NullRunGateIndeterminateError` (NR-P004),
  `NullRunUnknownActionError` (NR-P005) and
  `NullRunApprovalToolMismatchError` (NR-A017) are exported from the
  package root. `NullRunChainError` now covers the gateway's
  `CHAIN_KEY_MISMATCH` refusal.

- **Six new metric counters** are exported in `to_dict()`:
  `gate_indeterminate_total`, `unknown_action_total`,
  `policy_gate_indeterminate_total`, `ws_unverified_approval_total`,
  `ws_unverified_frame_total` and `dropped_llm_call_no_reservation`.

#### Fixed

- **A refused `/track` reaches the application.** The SDK asked the
  wrong question — it decided open-vs-closed by exception class while
  the gateway decides by error code. A refusal now raises, and the
  auto-instrumentation layer stops swallowing it. The payload is written
  to the write-ahead log before the raise, so a refusal is raised *and*
  recoverable.

- **A reservation id the SDK cannot bind is a refusal.** A gate answer
  carrying a `reservation_id` that is not a UUID now raises
  `NullRunMalformedGateResponseError` instead of proceeding with no
  reservation.

- **An SDK-internal fault in the `@protect` gate is a refusal.** The
  decorator's catch-all raised a transport-shaped error that rendered as
  HTTP 429 and category "decision". It now raises
  `NullRunGateIndeterminateError` and is counted on its own counter.

- **The LangChain callback obeys the same fail-CLOSED table as
  `@protect`.** `NullRunAuthenticationError`,
  `NullRunUnclassifiedRefusalError` and `NullRunRateLimitRedisError`
  now raise instead of vanishing through the callback.

- **Every MCP tool call runs its own `/gate` pre-flight.** The second
  and later MCP tool calls in one scope ran no pre-flight: no budget
  check, no reservation, no spend reserved for those calls.

- **The MCP adapter derives one envelope from the tool call.** The MCP
  path sent no `business_impact` and no `action_digest`, so an approval
  on that path could not be spent at all. The adapter now derives one
  envelope from the call it is about to make, plus that envelope's
  digest, and puts both on the wire.

- **The write-ahead log is scoped per user and per key.** The path was
  the same string for every user and every organization on the host, so
  two runtimes on one file destroyed each other's undelivered events.

- **The approval push reads the verified payload, not the outer body.**
  An unauthenticated approval frame is refused, counted and logged at
  ERROR, and the waiter stays parked and fails closed on the approval
  timeout.

- **A control-plane frame the client could have verified is refused.**
  A frame that arrives unsigned, or with a signature but no timestamp,
  is refused before any branch reads a field out of it.

- **An unknown control-plane action is refused, not silently dropped.**
  The dispatcher now raises `NullRunUnknownActionError` instead of
  logging and returning.

- **The error-code catalog names a class the dispatcher can build.**
  The catalog lagged the gateway registry by 34 codes, and the
  blocked-family dispatch arm matched by identity, so every typed
  subclass fell through to a generic fallback that raised `TypeError`.

- **Redaction follows the credential, not only the argument name.** A
  value-shaped pass runs beside the name-based one, so a secret that
  arrives under a name nobody listed is scrubbed.

- **No character of the API key reaches a log line.** Three places
  printed a fragment of the key, and they disagreed about how much. One
  helper answers it now.

- **The production detector is not a substring test.** A host that
  merely contained a dev marker was classified non-prod. Four ordered
  rules now decide.

- **The CI installs from the lock and pins every action.**

### 0.23.0 — 2026-10-29

Two enforcement paths that could not complete their own contract are
closed. The MCP path could not finish an approval round trip: a retry
after the operator approved was forwarded to the MCP server, so the
gateway never saw the grant. The zero-code LLM path booked the call
only after the provider had answered — the `llm_call` event is the only
thing that moves the budget counter, so a call the ceiling was supposed
to stop was counted instead of stopped.

There is no wire-protocol change. The public surface grows by ten
keyword-only parameters across four public methods, and one changed
return value.

#### Added

- **`MCPAdapter.call_tool` can carry an approval grant.** The method
  gains three named keyword-only parameters — `approval_id`,
  `business_impact`, `action_digest` — placed before `**passthrough`
  so they can never fall into the passthrough and be forwarded to the
  MCP server.

- **`NullRunRuntime.execute` gains `approval_id` and
  `tool_arguments`.** Both are appended after the existing parameters,
  so the positional order above them is unchanged. Each key reaches the
  wire only when the value is not `None`.

#### Changed

- **`check_workflow_budget` returns the reservation id.** The method
  gains `model`, `estimated_tokens`, `max_output_tokens` and
  `use_gate_cache`, and its return type changes from `None` to
  `str | None` — the server-minted reservation the gateway settles
  when the matching `/track` arrives, or `None` when no reservation was
  minted. Callers that ignored the return value are unaffected.

- **`NullRunRuntime.track` gains `reservation_id`.** The reservation
  travels with the cost event explicitly rather than through a
  context variable, which is one slot per task — two concurrent calls
  would swap reservations.

- **The zero-code LLM path reserves before the provider request.** A
  call the ceiling rejects never reaches the provider; the request is
  not sent at all. This is visible: a capped zero-code caller sees
  refusals where it saw successful calls that were billed anyway.

#### Fixed

- **The canonical argument bag reaches the wire.** The tool arguments
  travelled only as the legacy `input` field, so every params-based
  rule saw "no bag" and the approval decision had no argument snapshot
  to bind to. The same dict now reaches the wire as both `input` and
  `tool_arguments`.

### 0.22.2 — 2026-10-16

A status field that structurally could not report the failure it
existed to report, a packaging extra the SDK's own error message told
users to install but that was never declared, and a pre-flight that
priced at the input rate and so silently under-reserved every real LLM
call. None is a wire change.

#### Changed

- **`NullRunStatus` reflects a gateway that has actually been
  attempted.** A backend unreachable since `init()` used to read
  `backend_reachable=None`, so the degraded headline never fired.
  "Answered" means transport-level, not HTTP-2xx — a 402, 403 or 429
  is the gateway replying and stays reachable; only DNS, refused, TLS
  or timeout sets it false.

- **`pip install nullrun[websocket]` installs `websockets`.** The
  extra is declared with a floor of 14.0.

- **`set_call_context(max_output_tokens=…)` reaches `/gate`.** The
  pre-flight always sent `estimated_tokens=1`, which prices at the input
  rate and covers no output at all. The caller's declared cap is sent
  when set, and the key is absent — not present-and-null — when it is
  not.

### 0.22.1 — 2026-10-15

The SDK's public exception surface is restored. A QA pass found 24
classes the SDK raises that were not importable from the top-level
`nullrun` namespace. The classes existed, and enforcement was never
affected — only the documented public name was missing.

#### Added

- **24 more exception names are reachable via `from nullrun import X`.**
  The names are also added to `__all__`, so tab-completion and
  `from nullrun import *` reach them. Code that imports a missing name
  now succeeds.

#### Fixed

- **`on_policy_invalidated` fires on every WebSocket message.** The
  wrapper was an un-awaited coroutine, so the log line and the
  user-supplied callback never ran.

### 0.22.0 — 2026-10-09

The SDK's enforcement question can go to a local box that holds a
signed lease instead of to `api.nullrun.io`. The write-ahead log is
reworked around three loss paths: a `kill -9` while a refused event
was held, a 200 batch that hid per-item refusals, and a recovery that
unlinked the log before the events were provably safe.

Minor, not patch: the `/track` wire loses a field, and `/track` batch
refusals classify by whether the gateway already booked the spend.

#### Changed

- **A `CONSUME_OVERBUDGET` refusal that the gateway already booked is
  delivered, not quarantined.** The exception now carries a `recorded`
  tri-state (`True` / `False` / `None` for unparseable bodies) so a
  caller can tell the two apart. Code that watched the dead-letter
  queue for these events no longer sees them there.

- **`/track` no longer sends `cost_cents`.** The field was always
  zero and the gateway ignores it. `local_cost_cents` in the return
  value is unchanged.

- **4xx classification happens before quarantine, with a different
  answer per class.** `408` and `429` are re-queued and never
  dead-lettered. `401` and `403` stay in the log with a "blocked on
  the key" line — the data is valid and the key is rotated or revoked.
  `413` is the batch, not the events: the batch is halved and resent.
  `400` and `422` are bisected to a single event, so exactly one event
  is lost rather than the whole batch.

- **A held refusal survives `kill -9`.** The holdover is now in
  `<wal>.holdover` — deliberately not `.wal` and not `.inflight`.
  Recovery loads it as a hold, not a replay.

- **The `/track` batch path forwards the `provider` label.** Cached
  pricing differs by provider, and the two paths now agree.

- **The local box as the gate is opt-in.** Set `NULLRUN_EDGE_URL` and
  the enforcement question goes to a box holding a signed lease instead
  of to `api.nullrun.io`. `NULLRUN_EDGE_LEASE_ID` is required, not
  discovered — a box that chose its own budget enforces a number nobody
  granted. The mode refuses a silent fallback to the cloud, refuses a
  caller that writes the money, and treats an unreachable box as a
  refusal rather than a pass.

#### Security

- **The SDK never puts a price on the wire.** The field is absent from
  both a minimal and a fully populated payload.

- **The write-ahead log's guarantees are explicit, private and
  observable.** Files are created `0600` rather than through the
  process umask, mutations are serialised with an advisory lock, and
  the dead-letter size cap deletes nothing: at the cap the append is
  refused.

### 0.21.0 — 2026-10-02

The approval round trip closes. An operator approves an action and the
agent still cannot run it: the SDK sent a constant sentinel instead of
the business-impact envelope the gateway was looking for, and
classified refusals by what the SDK's wrapper assumed rather than by
what the wire said.

Minor, not patch: `BusinessImpact.tool_call()` is restored, the
`/track` path raises typed enforcement rejections where it dropped them
silently, and the `/gate` pre-flight routes through the typed
dispatcher.

#### Added

- **`BusinessImpact.tool_call()` is back.** Importable from
  `nullrun.business_impact`. The constructor emits exactly what the
  gateway's internally-tagged serialization produces, including
  `extractor_id` and `extractor_version`.

#### Changed

- **The v3 `/track` single path raises typed enforcement rejections
  instead of dropping them.** A 422 `CONSUME_OVERBUDGET` used to be a
  warning log line and a return value that treated the call as
  successful at the agent layer. It now raises
  `NullRunConsumeOverbudgetError`. Network errors and 5xx that name no
  enforcement failure still drop and log.

- **The `/gate` pre-flight types its refusal instead of assuming
  budget.** A rate-limit block, a tool block and a circuit-breaker
  trip used to reach the caller as `NullRunBudgetError` (NR-B004),
  which sends the operator looking for a spend-cap misconfiguration
  when the actual cause is a throttle policy. The dispatcher routes by
  wire code. A response with no machine-readable code still raises
  `NullRunBudgetError`.

#### Fixed

- **`@protect` binds approvals to something.** Since 0.18.5 every
  `@protect` call sent a constant `{"kind": "none"}` sentinel; a
  constant hashes to a constant, so the digest the gateway stored on
  the approval row matched the digest it recomputed at `/execute` for
  every tool — while binding the approval to nothing at all. The
  envelope is now carried on the call context, sent alongside the
  digest, and built before the `/gate` pre-flight so both hops hash
  the same bytes.

- **`status().ws_connected` reads a real attribute.** It was
  structurally pinned to `None`, so the never-established, live and
  dropped states collapsed into one.

### 0.20.0 — 2026-10-01

Every gate refusal is classified, and an unclassifiable one raises.
The SDK could read a body with no `category` as a permission.

Minor, not patch: an unclassifiable refusal now **raises** where
0.19.0 let the call proceed. That is a working loop becoming a
throwing one.

#### Added

- **`on_denied` selects the shape of a `denied` refusal and nothing
  else.** Default `"raise"`. Set `"message"` to get a
  `NullRunDeniedError` carrying the server-authored `agent_message` —
  the only text the SDK guarantees is safe to relay to a model. `budget`
  and `halt` keep their own exceptions even with the flag set.

#### Changed

- **A `/gate` body must state who decided before it counts as a
  verdict.** A body whose `decision_source` is absent or unrecognised
  raises `NullRunMalformedGateResponseError`. A hand-written `/gate`
  test double must now include `"decision_source": "gateway"`.

- **`NULLRUN_SENSITIVE_FAIL_OPEN` is refused against production**
  unless `NULLRUN_ALLOW_SENSITIVE_FAIL_OPEN=1` is set as well. The
  guard refuses the bypass rather than raising, so enforcement falls
  back to its own fail-CLOSED default and the attempt is logged at
  ERROR with a metric.

- **`NULLRUN_SKIP_BUDGET_CHECK` outside production logs and
  increments a metric** when it skips the check. Enforcement behaviour
  is unchanged.

- **`/execute` refusal bodies carry `category` and `agent_message`.**
  Additive on the wire.

#### Fixed

- **`@protect` no longer loses a LangChain tool when it is the outer
  decorator.** Applied to a `@tool` result, `@protect` wrapped the
  object with `functools.wraps` and returned a plain function, so
  `.invoke`, `.name` and `.args_schema` were gone and an agent loop
  could not bind the tool. A tool the loop cannot see raises no
  refusal. Both decorator orders now gate identically.

### 0.19.0 — 2026-09-30

The SDK-side bypasses found by an audit of the enforcement path are
closed: the gate answering the agent "allowed" on calls it had actually
blocked or never checked.

#### Removed

- **`NullRunRuntime.execute(..., mode="inline")` is gone.** It returned
  a synthesised local allow without contacting the gateway, so budget,
  rate-limit and tool-block policies were all skipped. It now raises
  `NullRunConfigError` (NR-S001). There is no replacement — every call
  goes through `/execute`. Drop the argument; `mode="auto"` (the
  default) already always contacts the gateway.

- **`register_strict_mode_forced` and `is_strict_mode_forced` are
  gone.** They existed only to force strict mode past the inline fast
  path, and had zero callers.

#### Changed

- **`MCPAdapter(runtime=None)` no longer means "do not gate".**
  `call_tool` was conditional on the runtime being present, and the
  runtime defaulted to `None` — so a default-constructed adapter called
  the MCP server with no `/execute` round-trip at all. `runtime=None`
  now means "resolve the global runtime", resolved lazily at
  `call_tool`. A missing API key raises rather than degrading to an
  ungated call. Passing `runtime=` explicitly still works and still
  wins.

#### Fixed

- **A real gate decision is no longer treated as a transport
  fail-open.** The LangChain / LangGraph callback swallowed
  `NullRunBlockedException` alongside transport errors. Enforcement
  exceptions are now re-raised through a deferred handoff to the
  `@protect` boundary.

- **A skipped pre-flight gate is countable.** The no-op increments
  `control_plane_no_workflow_total` /
  `budget_preflight_no_workflow_total` instead of being
  indistinguishable from normal operation.

### 0.18.5 — 2026-09-26

The public surface is reduced to the smallest set that still does the
job. Four entry points collapse into two, and a set of internals stops
being importable.

#### Changed

- **`nullrun.guard` replaces `nullrun.handle`.** Same `@contextmanager`
  body: it catches `NullRunError`, re-raises `WorkflowKilledInterrupt`
  untouched, prints a developer-facing report, and exits non-zero on
  failure. See [Error handling](#43-error-handling) for the
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
  auto-detection in [Framework integrations](#65-llm-frameworks)
  is unchanged.

#### Removed

These names are no longer importable from the top-level `nullrun`
namespace. At 0.18.5 the top-level namespace held exactly:

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

### 0.18.2 — 2026-09-22

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

See [Decorators & extractors](#72-decorators-context-managers) for the full
decorator reference and [Tool policies](#23-tool-policies)
for what the gate evaluates.

### 0.18.1 — 2026-09-22

Aimed squarely at the moment a developer first runs an example and it
does not work.

- **A four-line error report on the fail-fast paths.** A configuration
  or gate failure at startup prints what failed, where it failed (wire
  endpoint, status code, transport source), why it failed (the
  underlying exception and its machine `error_code`), and what to do
  about it. The end-user-facing message is still the headline, so an
  end-user deployment still sees a single clean sentence. See
  [Troubleshooting](#91-troubleshooting).

- **A warning when a protected tool fires 50 times with no model
  activity.** The usual cause is a tool wired up without the agent loop
  that feeds it, which otherwise bills nothing and looks like it works.

### 0.18.0 — 2026-09-21

- **Approved actions are consumed on success.** When an action runs
  after approval, the grant is closed automatically. Grants left open
  past their expiry no longer accumulate, so the approvals surface
  reflects only what is actually waiting on a human.

### 0.17.1 — 2026-09-15

- **Every gate call carries its own operation id.** A single id is no
  longer reused across calls in the same scope, which removes a class
  of spurious budget errors where an unrelated call inherited the identity
  of the first one. The error codes in
  [Error codes](#75-error-codes) are unchanged.

### 0.17.0 — 2026-09-12

- **The circuit breaker serialises sync and async callers against each
  other.** A threaded call and an `asyncio` call on the same breaker
  instance previously took different locks, so their state transitions
  could interleave. Both paths now contend on one lock. See
  [Circuit breaker](#21-circuit-breaker).

- **The impact helpers resolve off the top-level `nullrun` namespace**
  rather than needing a deep import into a private module. The helpers
  that [Sensitive tools](#24-sensitive-tools) describes are
  what this fixes; the exception they were raising on first call is
  gone.

### 0.16.x — August–September 2026

The hardening series. The surface settled here; everything above is a
change to it.

- **Kill propagates as an exception rather than an exit.** A
  `WorkflowKilledInterrupt` raised by [Kill](#44-control-plane-websocket)
  is not swallowed by an enclosing error handler, so an agent that is
  stopped from the control center stops. See
  [Control plane](#44-control-plane-websocket).

- **Policy fetches fail closed.** A policy the gate cannot retrieve is
  a refusal, not a pass. The enforcement path fails closed: the tool
  block, the aggregate rate limit and the budget check all refuse when
  their signal is missing. See [Policies](#22-policies).

- **Cost accounting is decimal, not floating point.** Amounts are
  serialized without binary-float drift, so a reserved cost and its
  consumption net to zero. See [Budgets](#31-budgets).

- **Reservations are released on the exception path.** A protected call
  that raises leaves no reservation behind.

---

Reports something that does not match what you are reading here? The
[GitHub](https://github.com/nullrunio/nullrun-docs) link in the footer
points at this docs repository. Open an issue there.

---

*End of printable documentation.*

*This document was generated from [docs.nullrun.io](https://docs.nullrun.io).
For the latest version, always refer to the live site.*