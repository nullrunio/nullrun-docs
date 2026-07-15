# NullRun Docs

Source for the **[docs.nullrun.io](https://docs.nullrun.io)** site.

## What's inside

- **[Getting started](docs/getting-started/install.md)** — install,
  quickstart, SDK configuration.
- **[Concepts](docs/concepts/circuit-breaker.md)** — how budgets,
  circuit breaker, control plane, sensitive tools, and workflow
  context work.
- **[How-to](docs/how-to/langgraph.md)** — recipes for specific
  frameworks and scenarios (LangGraph, OpenAI Agents, cost cap).
- **[Reference](docs/reference/sdk-api.md)** — full SDK / HTTP API
  / error codes reference.

## Where to start

| If you want to... | Open |
| --- | --- |
| Try it in 5 minutes | [Quickstart](https://docs.nullrun.io/getting-started/quickstart/) |
| Wire up the SDK for production | [Configuration](https://docs.nullrun.io/getting-started/configuration/) |
| Track or cap spend | [Budgets](https://docs.nullrun.io/concepts/budgets/) + [Cost cap how-to](https://docs.nullrun.io/how-to/cost-cap/) |
| Use LangGraph | [How-to → LangGraph](https://docs.nullrun.io/how-to/langgraph/) |
| Use OpenAI Agents | [How-to → OpenAI Agents](https://docs.nullrun.io/how-to/openai-agents/) |
| Debug 4xx / 5xx responses | [Error codes](https://docs.nullrun.io/reference/errors/) |
| See the full SDK surface | [SDK API reference](https://docs.nullrun.io/reference/sdk-api/) |

## Full page list

**Getting started**
- [Install](docs/getting-started/install.md) · `pip install nullrun`, API key, auto-instrumentation
- [Quickstart](docs/getting-started/quickstart.md) · `@protect` in 30 lines
- [Configuration](docs/getting-started/configuration.md) · env vars, transport options, gRPC status

**Concepts**
- [Circuit breaker](docs/concepts/circuit-breaker.md) · CLOSED / OPEN / HALF_OPEN, `PERMISSIVE`/`STRICT`/`CACHED` fallback modes
- [Budgets](docs/concepts/budgets.md) · v3 contract: `/gate` pre-flight + server-minted `reservation_id` + `/api/v1/track` single commit
- [Sensitive tools](docs/concepts/sensitive-tools.md) · fail-CLOSED, always
- [Workflow context](docs/concepts/workflow.md) · `nullrun.workflow(...)` + `nullrun.chain(...)` + `parent_trace_id` multi-agent attachment
- [Control plane (WebSocket)](docs/concepts/control-plane.md) · real-time kill / pause / `approval_resolved`
- [API keys](docs/concepts/api-keys.md) · scopes, `expires_at`, rotation, revocation
- [Policies](docs/concepts/policies.md) · RateLimit / BudgetLimit / ToolBlock, org vs workflow, aggregation
- [Tool policies](docs/concepts/tool-policies.md) · glob match, 4 KB cap, union across scopes
- [Loop detection](docs/concepts/loop-detection.md) · window-based exact-match, trips the breaker
- [Anomaly detection](docs/concepts/anomaly-detection.md) · `mean + N·σ`, Lite / Moderate / Strict
- [Human approval](docs/concepts/human-approval.md) · pause + Slack/Email/Webhook fanout

**How-to**
- [Protect a LangGraph agent](docs/how-to/langgraph.md)
- [Use with OpenAI Agents](docs/how-to/openai-agents.md)
- [Set a hard cost cap](docs/how-to/cost-cap.md)

**Reference**
- [SDK API](docs/reference/sdk-api.md) · `init`, `@protect`, `@sensitive`, `workflow`, exceptions
- [HTTP API](docs/reference/http-api.md) · `/track`, `/gate`, `/capabilities`, `/heartbeat`, WebSocket
- [Error codes](docs/reference/errors.md) · `validation_error`, `RateLimitError`, kill contract

**Compliance**
- [Overview](docs/compliance/index.md) · Fortress posture, fail-CLOSED matrix
- [Geographic restrictions](docs/compliance/geo-restrictions.md) · IP-level geo-block, sanctioned + high-risk blocklists, VPS runbook
- [Sanctions screening](docs/compliance/sanctions-screening.md) · OFAC SDN signup screening, degraded fallback

## What you need from us

- **API key** — create one in [nullrun.io](https://nullrun.io) → Settings
  → API keys. You get a `nr_live_…` public identifier. The SDK
  transparently obtains the HMAC signing secret via
  `POST /api/v1/auth/verify` on first use.
- **Python ≥ 3.10** for the SDK.
- **Nothing else to read the docs** — the site is public.

## Other NullRun repositories

- [nullrun-sdk-python](https://github.com/nullrunio/nullrun-sdk-python) — Python SDK (`pip install nullrun`)
- [nullrun-examples](https://github.com/nullrunio/nullrun-examples) — runnable examples
- [.github](https://github.com/nullrunio/.github) — organisation profile, SECURITY / SUPPORT
- `nullrun` — gateway + dashboard (private repository, access on request)
