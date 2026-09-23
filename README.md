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
- [Budgets](docs/concepts/budgets.md) · `/gate` pre-flight + server-minted `reservation_id` + `/api/v1/track` single commit
- [Sensitive tools](docs/concepts/sensitive-tools.md) · fail-CLOSED, always
- [Workflow context](docs/concepts/workflow.md) · `nullrun.workflow(...)` + `nullrun.chain(...)` + `parent_trace_id` multi-agent attachment
- [Control plane (WebSocket)](docs/concepts/control-plane.md) · real-time kill / pause / `approval_resolved`
- [API keys](docs/concepts/api-keys.md) · scopes, `expires_at`, rotation, revocation
- [Policies](docs/concepts/policies.md) · RateLimit / BudgetLimit / ToolBlock, org vs workflow, aggregation
- [Tool policies](docs/concepts/tool-policies.md) · glob match, 4 KB cap, union across scopes
- [Human approval](docs/concepts/human-approval.md) · typed `BusinessImpact` + `action_digest` action-bound grants
- [Error handling](docs/concepts/error-handling.md) · ErrorContext, multi-layer fail-CLOSED

**How-to**
- [Protect a LangGraph agent](docs/how-to/langgraph.md)
- [Use with OpenAI Agents](docs/how-to/openai-agents.md)
- [Set a hard cost cap](docs/how-to/cost-cap.md)

**Reference**
- [SDK API](docs/reference/sdk-api.md) · `@protect` (canonical), `@sensitive(impact=...)` (advanced), `workflow`, exceptions
- [HTTP API](docs/reference/http-api.md) · `/track`, `/gate`, `/capabilities`, `/heartbeat`, WebSocket
- [Error codes](docs/reference/errors.md) · `validation_error`, `RateLimitError`, kill contract

**Compliance**
- [Overview](docs/compliance/index.md) · geo-block and sanctions-screening posture
- [Geographic restrictions](docs/compliance/geo-restrictions.md) · IP-level geo-block, sanctioned + high-risk blocklists, VPS runbook
- [Sanctions screening](docs/compliance/sanctions-screening.md) · OFAC SDN signup screening, degraded fallback

## What you need from us

- **API key** — create one in [nullrun.io](https://nullrun.io) → Settings
  → API keys. You get a `nr_live_…` public identifier. The SDK
  transparently obtains the HMAC signing secret via
  `POST /api/v1/auth/verify` on first use.
- **Python ≥ 3.10** for the SDK.
- **Nothing else to read the docs** — the site is public.

## Deployment

Two parallel workflows ship from this repository. Until DNS is cut over,
traffic flows through the **active** origin (GitHub Pages); the
**standby** origin (Cloudflare Pages) stays current on every push so the
switchover is a one-record change at the registrar.

| Workflow | Target | DNS origin | Status |
| --- | --- | --- | --- |
| `.github/workflows/docs.yml` | GitHub Pages | `nullrunio.github.io` (CNAME at netim.net) | **Active** |
| `.github/workflows/pages-cf.yml` | Cloudflare Pages | `<project>.pages.dev` (CF-provisioned) | **Standby** |

### Current security posture

Mozilla Observatory scores each header in the response:

| Test | GitHub Pages (current) | Cloudflare Pages (after cutover) |
| --- | --- | --- |
| Content-Security-Policy | passes (meta-tag form) | passes (HTTP header) |
| Referrer-Policy | passes (meta-tag form) | passes (HTTP header) |
| Strict-Transport-Security | ❌ (GitHub Pages forbids) | ✅ (1 year, includeSubDomains) |
| X-Content-Type-Options | ❌ | ✅ `nosniff` |
| X-Frame-Options | ❌ | ✅ `DENY` |
| Permissions-Policy | ❌ | ✅ (camera, mic, geo, etc. disabled) |
| Cross-Origin-Opener-Policy | ❌ | ✅ `same-origin` |
| Cross-Origin-Resource-Policy | ❌ | ✅ `same-origin` |

GitHub Pages does not allow custom HTTP response headers — the
`<meta http-equiv>` form in `overrides/main.html` covers the two tests
that accept it; the remaining six tests require the HTTP-header form in
`docs/_headers`, which only Cloudflare Pages can serve. See the comment
block at the top of `docs/_headers` for the per-header credit map.

### One-time cutover procedure

1. In the Cloudflare dashboard, create a Pages project pointing at this
   repo, branch `master`, build command `mkdocs build --strict`,
   output directory `site/`.
2. Add the custom domain `docs.nullrun.io` to the project. Cloudflare
   issues the certificate and shows the target CNAME
   (`<project>.pages.dev`).
3. Add two GH repository secrets: `CLOUDFLARE_API_TOKEN` (Pages Edit
   permission) and `CLOUDFLARE_ACCOUNT_ID` (from the CF dashboard URL).
4. At the registrar (netim.net), change the CNAME record for
   `docs.nullrun.io` from `nullrunio.github.io.` to the
   `<project>.pages.dev.` value CF provided. DNS propagation: ~5 min
   on Fastly's resolver, up to 48 h elsewhere.
5. Re-run the [Mozilla Observatory
   scan](https://developer.mozilla.org/en-US/observatory/analyze?host=docs.nullrun.io).
   Expected grade: **A+**.
6. After the cutover, disable `.github/workflows/docs.yml` to stop
   the duplicate GitHub Pages deploy.

The `<meta http-equiv>` tags in `overrides/main.html` stay in place as
a defence-in-depth fallback — they have no effect when the equivalent
HTTP headers are present, and they keep the site partially hardened if
the site ever has to fall back to a host without header injection.

## Other NullRun repositories

- [nullrun-sdk-python](https://github.com/nullrunio/nullrun-sdk-python) — Python SDK (`pip install nullrun`)
- [nullrun-examples](https://github.com/nullrunio/nullrun-examples) — runnable examples
- [.github](https://github.com/nullrunio/.github) — organisation profile, SECURITY / SUPPORT
- `nullrun` — gateway + dashboard (private repository, access on request)
