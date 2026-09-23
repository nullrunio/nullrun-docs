title: Tracing
maturity: stable
description: OpenTelemetry-style spans for every gate decision, with parent_trace_id propagation so the dashboard renders a true waterfall.
# Tracing

A **trace** is everything that happened during one run of your agent.
In the dashboard they live under **Executions** and **Traces** in the
sidebar. Each execution is one agent run; the trace view shows the
nested structure of every LLM call, every tool call, and how long
each took.

If a user reports "the agent did something weird at 14:30", the
tracing tab is where you go to see exactly what happened.

## What you see in the dashboard

The **Executions** page lists every agent run. Each row shows:

- **Workflow** — which workflow ran this
- **Started at** — timestamp
- **Duration** — total run time
- **Status** — completed / failed / killed
- **Cost** — total cost for this run
- **LLM calls** — how many LLM invocations

<figure class="nr-shot">
  <img class="nr-shot__light" src="../../assets/images/screenshots/executions-light.png"
       alt="Executions page listing every agent run with workflow, duration, status and cost columns.">
  <img class="nr-shot__dark" src="../../assets/images/screenshots/executions-dark.png"
       alt="Executions page listing every agent run with workflow, duration, status and cost columns.">
  <figcaption class="nr-shot__caption">Executions</figcaption>
</figure>

<figure class="nr-shot">
  <img class="nr-shot__light" src="../../assets/images/screenshots/traces-light.png"
       alt="Traces page with the waterfall of LLM and tool calls for a single execution.">
  <img class="nr-shot__dark" src="../../assets/images/screenshots/traces-dark.png"
       alt="Traces page with the waterfall of LLM and tool calls for a single execution.">
  <figcaption class="nr-shot__caption">Traces · Waterfall</figcaption>
</figure>

Click an execution to open the **Trace** view. The trace is a
hierarchical tree:

```
Run "user-123-research"     2m 14s   $0.42
├─ Step 1: plan             0.3s    $0.01
│  └─ llm.call (claude-sonnet-4-5)    0.3s    $0.01
├─ Step 2: research         45s     $0.18
│  ├─ llm.call (claude-sonnet-4-5)    12s     $0.06
│  ├─ tool.call (tavily_search)       8s      —
│  └─ llm.call (claude-sonnet-4-5)    22s     $0.12
├─ Step 3: write             30s     $0.12
│  └─ llm.call (claude-sonnet-4-5)    30s     $0.12
└─ Step 4: review            17s     $0.11
   └─ llm.call (claude-sonnet-4-5)    17s     $0.11
```

Three things you can read off this tree at a glance:

- **Where the time went** — the longest step is where to optimise.
- **Where the money went** — same, but for cost.
- **What the agent did** — each tool call and LLM call is
  clickable, showing the full request/response.

## How a trace is built

When you use the SDK's `@protect` decorator or `with workflow(...)`
context manager, the SDK automatically creates spans:

| Action | What gets a span |
|---|---|
| `@protect` decorator | One span per gate call |
| `with workflow("name"):` | One span for the whole workflow run |
| `with chain("id"):` | One span for the chain |
| `with span("phase"):` | One span for the named phase |

You don't have to add tracing manually — it comes from the
decorators and context managers you already use. The SDK sends
trace metadata alongside every `/gate` and `/track` call.

For nested agent orchestrations (a supervisor calling sub-agents),
each sub-agent's spans are nested under the supervisor's. The trace
view shows the tree; the **Cost** column rolls up automatically.

## What each span contains

Click any span in the trace tree to see:

- **Span ID** — unique identifier (UUID)
- **Parent span ID** — for nesting
- **Started at** / **Duration** — timing
- **Status** — completed / failed / killed
- **Inputs** — the prompt metadata sent to the LLM (truncated if
  huge). **Prompt content is NOT stored** — NullRun never persists
  raw prompt text or LLM response bodies. See
  [Audit records → What is NOT stored](../concepts/error-handling.md#what-is-not-stored).
- **Outputs** — the LLM's response metadata (token counts, model,
  finish reason). **Raw completions are NOT stored.**
- **Cost** — input + output tokens × model rate
- **Tool calls** — every tool the span invoked (with arguments)
- **Decision** — the gate verdict (`allow` / `block` /
  `require_approval`) and which policy triggered it

For blocked calls, the **Decision** row is the most useful — it
links to the policy that matched and shows the rule.

## How long traces are kept

Trace retention follows your plan's `history_days` window:

| Plan | Trace retention |
|---|---|
| Lite | 3 days |
| Starter | 7 days |
| Growth | 30 days |
| Scale | 90 days |
| Enterprise | unlimited |

After the retention window expires, the trace is removed from the
dashboard; the aggregated cost information stays (it's summarised
per workflow per period).

The retention window is independent of the trace *generation* caps
— Lite also throttles to **10 000 tokens/hour** and **75 000
executions/month** (see [Billing & Plan → Per-tier caps](billing.md#per-tier-caps)),
so a Lite workflow's traces stop accumulating well before the 3-day
window applies.

If you need longer retention for compliance, you can export traces
from the dashboard as JSON via the **Export** button on the
Executions page. The exported shape matches the wire format.

## Span identifiers and correlation

Each span has three identifiers:

| Field | Purpose |
|---|---|
| `trace_id` | The whole agent run — same across every span in one execution |
| `span_id` | One call — unique per `@protect` invocation |
| `parent_trace_id` | For sub-agents — the orchestration trace they belong to |

You can search the dashboard by any of these. If a customer reports
a problem with `trace_id = abc-123`, you can pull the full trace and
every decision tied to it from the audit log.

## How to use tracing during development

When you're building a new agent, traces tell you:

- **Is the agent slow?** — sort by duration, see which LLM call
  takes the most time.
- **Is the agent hitting the budget?** — look for spans with
  `decision = block / NR-B004`.
- **Is the agent calling tools you didn't expect?** — the trace
  shows every tool call with arguments.

When you're debugging a production issue, traces answer:

- **What did the agent do at 14:30 yesterday?** — filter by time
  range, click each execution, walk the trace.
- **Why did the call to `send_email` fail?** — the trace shows
  the call's status and decision. If it was blocked, the linked
  policy explains why.
- **How much did this single run cost?** — the top of the trace
  shows the total; the leaves show the per-call breakdown.

## Common questions

### "My trace shows nothing"

If the runtime was never created (the first `@protect` call never
fired) or the API key is missing, the SDK runs in error mode and no
spans are recorded. Check the SDK logs for
`NullRunAuthenticationError`.

### "My trace is incomplete — only some spans show up"

The SDK buffers events and flushes on a timer. If your process
crashes before the flush, the in-flight spans are lost. Use
`nullrun.shutdown(flush=True)` in your `finally` block to ensure
everything reaches the gateway.

### "Why are some spans duplicated?"

The SDK's auto-instrumentation emits one span per LLM call. If you
also call `track_llm` manually for the same call, you'll see two
spans. Pick one or the other — the auto-instrumentation is enough for
the standard OpenAI / Anthropic / Gemini / Cohere clients.

## See also

- [Workflow context](workflow.md) — how `workflow()` scopes spans
- [Error handling](error-handling.md) — errors that span blocks
- [Reference → SDK API → track_*](../reference/sdk-api.md) — manual
  span creation

## Deep dive

### Mechanism

The trace ingest path is `proxy/middleware/tracing.rs:64-132`
(`trace_middleware`). On every inbound request the middleware reads
the `traceparent` header (W3C Trace Context format:
`version-trace_id-span_id-flags`), parses it via
`TraceContext::from_traceparent` (line 29-41), and stashes it in
request extensions so handlers can read `get_trace_id(request)` or
`get_trace_context(request)`. The parsed context is forwarded into
the trace ingest at `proxy/handlers.rs:process_span_events_batch`
(ADR-014) where `traces.w3c_trace_id` and `spans.w3c_parent_span_id`
get populated as sibling columns — the SDK-minted UUID remains the
primary key (`TraceRow.w3c_trace_id` is nullable,
`backend/src/db/mod.rs:454-458`). The read path is
`backend/src/proxy/http/traces.rs:1-` — the org-scoped list endpoint
fetches trace summaries plus per-trace span batches (capped by
`MAX_SPANS_PER_TRACE`, default `DEFAULT_SPANS_PER_TRACE = 10`,
`:81`) and redacts PII via `proxy::redaction::Redactor` before
serialization. The single-trace endpoint
(`GET /api/v1/orgs/:org_id/traces/:trace_id`) reconstructs the
waterfall tree from `spans.parent_span_id` (DB schema migration
141 at `db/mod.rs:4506-4532`).

### Guarantees

W3C header extraction is best-effort — a missing or malformed
`traceparent` MUST NOT block ingest (ADR-014 §"Compliance"). When
the header is absent, `w3c_trace_id` is `NULL` and the trace
remains queryable by its SDK-minted UUID. The audit chain retains
the SDK-minted UUID as the canonical identity even when
`w3c_trace_id` is populated, so no JOIN / index / FK is re-typed.
A sparse partial index `idx_traces_w3c_trace_id_partial` keeps the
secondary-identifier index bounded (ADR-014 §"Cons"). Per-plan
retention is enforced by `backend/src/workers/decision_history_retention.rs`
which reads `plans.features.history_days` live from the DB; the
canonical values are 3 (Lite), 7 (Starter), 30 (Growth), 90
(Scale), -1 unlimited (Enterprise) — pinned by migration 002 and
the inline `plans` table seeding at `db/mod.rs:1994-2011`. Span
rows carry a typed `verdict` column (`'allow'` / `'flag'` /
`'block'` / `'chain'`, migration 274) that replaced the
3-tier frontend heuristic; DB CHECK constraint enforces the
four-value domain.

### Patterns

The auto-instrumentation emits one span per LLM call and one per
`@protect` invocation; `with workflow()` / `with chain()` /
`with span()` context managers emit a parent span that the per-call
spans nest under. Sub-agent orchestration propagates the W3C
`traceparent` so a supervisor's child spans appear under the
supervisor's trace_id in the waterfall. Per-trace PII redaction is
applied at the read boundary (`traces.rs:Redactor` usage, line 72)
— allowlist inside the config keeps well-known identifier fields
(`span_id`, `trace_id`, `w3c_trace_id`, `w3c_parent_span_id`)
intact, but everything else in `metadata` / `name` / `error` /
`root_span_name` runs through the deny-list redactor before
serialization. The `decision` field on a span is `verdict` — never
`metadata.policy_decision` (the frontend's previous heuristic
fallback was deleted in migration 274). When the SDK process
crashes before the buffer flush, in-flight spans are lost — that's
why `nullrun.shutdown(flush=True)` is required in the `finally`
block.

### Approaches

ADR-014 chose Path B (sibling `w3c_trace_id` / `w3c_parent_span_id`
columns) over Path A (rename `trace_id` to W3C hex). The reasons
were: backward-compat (existing SDKs that don't extract
`traceparent` continue to write `NULL`), no FK changes (every
JOIN and audit-chain reference is unchanged), forward-compat (a
future rename to W3C hex becomes a key-swap, not a re-typing),
and OTLP-friendly (a future `nullrun-otlp-exporter` can read
`w3c_trace_id` and emit it as the OTLP trace ID). The
typed-`verdict`-column fix (F-27, migration 274) was chosen over
the alternative of "frontend keeps the heuristic" because the
audit log + dashboard would otherwise disagree on the decision
label. Span retention is per-plan, not global — the alternative
considered (single retention floor) was rejected because Scale
and Enterprise customers have materially different cost-to-store
trade-offs.

### Limitations

Retention is independent of the trace *generation* caps — Lite
throttles at 10 000 tokens/hour and 75 000 executions/month
(`db/mod.rs:1994` features payload), so traces stop accumulating
well before the 3-day window applies. After the retention window
expires, the trace is removed from the dashboard; the aggregated
cost information is summarized per workflow per period and
survives. The W3C header extraction is best-effort and best-effort
on the SDK side too — only SDKs that call the W3C propagation
helper populate `w3c_trace_id` (others leave it `NULL`). The
partial index on `w3c_trace_id` keeps lookup bounded but means a
full UUID join remains the path for legacy SDKs. The frontend's
`SpanRow.tsx` previously used a 3-tier heuristic
(`metadata.policy_decision → name-suffix → status`) that disagreed
with the backend's typed `verdict` column; the migration is closed
in `verdict` typed column. The trace ingest batches via
`process_span_events_batch` — there is no synchronous per-span
INSERT path; back-pressure on the batch buffer shows up as dropped
spans during high traffic. Per-trace span count is capped
(`MAX_SPANS_PER_TRACE`) and the response marks truncated rows via
`truncated_trace_ids` so the dashboard can show a "show more"
indicator.
