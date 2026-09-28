---
title: Performance & limits
maturity: stable
description: Latency budgets, failure-mode behaviour, integration limits, and timeout handling — for technical buyers evaluating NULLRUN.
---

# Performance & limits

A consolidated reference for technical buyers evaluating NULLRUN's
operational characteristics. Every value below reflects the deployed
product; rows marked **Not measured** are honest gaps — we surface what
we don't know rather than quote a number we haven't earned.

This page is the load-bearing complement to the
[Circuit breaker](../concepts/circuit-breaker.md) and
[Error handling](../concepts/error-handling.md) concept pages:
those explain the *what* and *why*, this page enumerates the
*bounds*.

## Hot-path latency

The gate hot path is **`/api/v1/gate`** → an atomic budget reservation
against the budget store → an audit outbox write to the state store.
Wall-clock budgets are layered; the inner cap is the binding one.

| Stage | Bound |
| --- | --- |
| Outer HTTP request (`/api/v1/*`) | **30 s** (env `REQUEST_TIMEOUT_SECS`, default 30) |
| `/api/v1/gate` inner hard timeout | **5 s** (`GATE_HANDLER_HARD_TIMEOUT`) |
| Gate orchestrator inner hard timeout | **3 s** (`ORCHESTRATOR_HARD_TIMEOUT`) |
| `/api/v1/execute` inner timeout | **None** — relies on outer 30 s + budget-store breaker fail-fast (<100 ms once tripped) |
| `/api/v1/track` inner timeout | **None** — relies on outer 30 s |
| Reservation scan loop cap | **256 iterations** |
| Reservation scan page size | **1 000** keys per iteration (256 k slot visits worst case) |
| Partial-scan reservation result | typed result carrying the reserved and projected amounts — fail-CLOSED 402, never silent truncation |

Both stores sit behind bounded connection pools, and those bounds are
part of the observed latency envelope. Against the budget store the pool
holds at most **32** connections; a caller waiting for a connection to
become free gives up after **5 s**, and a caller that cannot open a new
connection at all gives up after **10 s** (clamped to the 1–60 s range).
The state-store pool gives up waiting for a connection after **10 s** and
caps each individual statement at **30 s** per connection.

### Healthy-path budget

When the budget store is healthy and no `/check` style fan-out is
required:

1. Network RTT to the budget store: sub-millisecond within a region.
2. The single atomic reservation step: <5 ms typical, <50 ms at p99.
3. Orchestrator evaluation: <2 ms typical.
4. Total `/api/v1/gate` server-side: **<10 ms typical, <60 ms p99**.

The 3 s orchestrator cap is the binding inner budget; the 5 s gate
handler cap is a one-above safety net. The 30 s outer request timeout
should never fire against a healthy budget store.

### First-burst (breaker not yet tripped)

If the budget store is reachable but slow, the worst case before the
breaker trips is:

- 1 connection open × 10 s + 1 pool wait × 5 s + 1 scan cap × ~50 ms ≈ **up to 15 s**
- On the 5th consecutive failure, the breaker trips and subsequent
  calls short-circuit **sub-100 ms** returning the budget-store
  unavailable response (see [Budget store failure](#budget-store-failure) below).

### Not measured

- Real p99 RTT to the budget store at production scale for the
  worst-case reservation path (256 scan iterations + 256 bulk reads
  ≈ 512 operations).
- Worst-case first-request latency on a budget-store partition before
  the breaker trips.

## Behaviour when a service is unavailable

Every enforcement-path failure mode below is **fail-CLOSED** unless
explicitly noted. The default posture is "do not let the agent proceed
when an enforcement signal is missing".

### Budget store failure

The budget-store circuit breaker has three profiles, picked by
call-site:

| Profile | Consecutive failures | Recovery window | Half-open probes | Used for |
|---|---|---|---|---|
| **default** | 5 | 30 000 (30 s) | 1 | Generic budget-store paths |
| **critical** | 3 | 60 000 (60 s) | 1 | Budget enforcement on the gate hot path (fail-CLOSED) |
| **high-traffic** | 20 | 10 000 (10 s) | 3 | Buffered / stale-cache / analytics paths |

The breaker short-circuits in **sub-100 ms** once open.

| Failure point | HTTP | Behaviour |
| --- | --- | --- |
| Atomic reservation failure on the gate path | **402** | fail-CLOSED — the call is blocked, never the client |
| Per-org aggregate rate-limit bucket unavailable | **503** | fail-CLOSED |
| Idempotency store unavailable | **503** | fail-CLOSED |
| Sub-workflow depth cycle-walk lookup fails | **503** | fail-CLOSED |
| Invoke-persist step fails | **503** | fail-CLOSED |
| Inline pre-check on `/track` idempotency | varied | fails through to the generic error envelope |

**Retry behaviour:** no automatic retry in the
reservation/consume/idempotency handlers — failures surface directly to
the breaker. The breaker is the retry mechanism.

Every reservation outcome maps to a fixed HTTP status. A hard budget
block, an org ceiling, a workflow budget, an overdraft cap, an anti-DoS
reserved cap, and a partial reservation scan all return **402**; the
first two carry the public wire codes `BUDGET_HARD_BLOCKED` and
`BUDGET_ORG_CEILING_BLOCKED`. A consume-side budget overrun returns
**429** with `Retry-After: 1`, and a consume overshoot — actual cost
above the reservation — returns **422** with the public code
`CONSUME_OVERBUDGET`. A reservation whose TTL has expired or that is
otherwise orphaned returns **503**, and a broken invariant on an
unconfigured policy returns **500**.

### State store failure

The state-store connection pool is sized at `min(cores, 12) × 2 + 10`
connections — roughly 25–34 on a 12-core host. Idle connections are
released after **600 s** and retired after **1 800 s** (which protects
against DNS and connection-pooler rollover). A session that is idle
inside an open transaction is terminated after **60 s**, and an
individual statement is capped at **30 s** per connection. The state
store has its own circuit breaker that mirrors the default profile
(5 consecutive failures, 30 s recovery), and it short-circuits in
**<100 ms** once open.

#### `/track` outbox path (the only enforcement-side state-store write)

The audit-row insert is **best-effort and off the request path**:

- The write runs through the state-store circuit breaker in
  degraded mode.
- On insert error: a warning is logged, the connection error is
  recorded as a metric, and the request **continues** — the gate
  response is unchanged. The audit row is not on the critical path.
- A background drain worker picks the rows up on a fast ticker.
- Drain tick interval: **5 s** default, clamped to the 2–300 s range.
- Per-tick batch size: **100**.
- Per-tick timeout: **30 s**.
- Per-row backoff: **1 / 2 / 4 / 8 / 16 s** exponential.
- Consecutive-error cap per tick: **5** (tick break on persistent errors).
- Dead-letter at `retry_count >= 5`: hard ceiling.
- Permanent failures are dead-lettered immediately rather than retried.
- Retention once dead-lettered: **30 days**.

#### Other outbox partitions

| Partition | `max_attempts` | Backoff base |
|---|---|---|
| governance | **3** | 30 s × 2^attempt + jitter |
| notification | **5** | 30 s × 2^attempt + jitter |
| analytics | **1** (fire-and-forget) | — |

### Upstream LLM / provider failure

The provider module is sparse — only the OpenAI provider is
registered; Anthropic / Google / Azure types exist but are not
registered, and `/api/v1/proxy*` is not wired into the live router.

| Thing | Value |
| --- | --- |
| OpenAI HTTP client timeout | **Not configured** — no connect, read, idle-pool, or TCP-keepalive setting |
| Provider retry | **None** — one outbound call per invocation, immediate return |
| HTTP status on provider failure | bare `502 BAD_GATEWAY` — no `error_code`, no `Retry-After`, no JSON envelope |
| OpenAI `429` parse | rate-limit hint is **dropped on the floor** — the **60 s value is never emitted as `Retry-After`** |
| Streaming failure shape | the governance event carries the error text, but the HTTP status stays 200 |

This is the area with the **largest gap** between SDK promise and
backend reality. Practical implication: a hung OpenAI socket stalls
until the outer 30 s request timeout fires; there is no per-call
connect timeout, no retry, and no machine-readable error envelope.

## Timeouts and integration limits

### HTTP / WebSocket / SSE

| Surface | Setting | Value |
| --- | --- | --- |
| `/api/v1/*` outer request | request-level timeout | **30 s** |
| HMAC re-read cap (`MAX_BODY_SIZE`) | body cap before HMAC verify | **10 MiB** |
| WebSocket server ping interval | `Message::Ping(vec![])` | **30 s** |
| WebSocket HMAC replay window | `WS_HMAC_MAX_AGE_SECONDS` | **300 s** |
| WebSocket idle disconnect | **None** — closed only on Close frame / stream error / send failure | — |
| WebSocket per-org connection cap | **None** (SSE has `MAX_SSE_PER_ORG=5`) | — |
| WebSocket max frame / message size | **None configured** — axum defaults apply | — |
| SSE max connection duration | hard cap | **24 h** |
| SSE JSON heartbeat cadence | informational heartbeat | **30 s** |
| SSE protocol-level keepalive (axum `KeepAlive`) | text `"ping"` | **15 s** |
| SSE per-org concurrent cap | `MAX_SSE_PER_ORG` | **5** |
| EventBus default capacity | bounded queue | **4 096 events** (overflow at **3 072 / 75%**) |
| Slow-consumer signal | server emits `WsMessage::ResyncRequired` to force SDK reconnect | — |

### OAuth / webhook clients (cold path)

| Client | Total timeout | Connect timeout |
| --- | --- | --- |
| GitHub OAuth | **10 s** | **5 s** |
| Google OAuth | **10 s** | **5 s** |
| SSO | **10 s** | **5 s** |
| Cron egress (litellm pricing) | **10 s** | **5 s** |
| Slack `chat.postMessage` | **10 s** | none (covered by the total timeout) |

### HMAC policy

| Setting | Value |
| --- | --- |
| `NULLRUN_HMAC_REQUIRED` default | `false` (warns at runtime) |
| `NULLRUN_HMAC_MAX_AGE_SECS` default | **300 s** |
| `NULLRUN_CONSUME_RACE_WINDOW_SECONDS` default | **2 s**, clamped `[0..30]` |
| HMAC-verified SDK paths | `["/api/v1/check", "/api/v1/execute", "/api/v1/gate", "/api/v1/track", "/api/v1/track/batch"]` |
| Gateway signing key min length | **32 bytes** (env `NULLRUN_GATEWAY_SIGNING_KEY`) |

### Webhook signature replay windows

| Webhook | Algorithm | Replay window |
| --- | --- | --- |
| Slack Events | HMAC-SHA256 over `v0:{ts}:{raw_body}`, header `X-Slack-Signature: v0=<hex>` | **300 s** |
| Slack OAuth state | TTL | **600 s** |
| Slack install ticket | TTL | **300 s** |
| Polar | Stripe-shaped `t=<unix>,v1=<hex>` over `timestamp.payload`, HMAC-SHA256, raw bytes | **300 s** |
| Polar sandbox mode | dev-only — verification bypassed (production requires signed webhooks) | — |
| Stripe | **Not supported** — Polar is the sole payment provider | — |

## Hard limits and caps

### Body / payload caps

| Cap | Value |
| --- | --- |
| HTTP request body cap | **10 MiB** (`10 * 1024 * 1024`) |
| MCP discovery SSE chunk | **65 536 bytes** (64 KiB) |

### Validation caps

| Constant | Value |
| --- | --- |
| `MAX_WORKFLOW_NAME` | **80** |
| `MAX_POLICY_NAME` | **80** |
| `MAX_API_KEY_NAME` | **80** |
| `MAX_ORG_NAME` | **100** |
| `MAX_ALERT_RULE_NAME` | **80** |
| `MAX_KILL_REASON` | **500** |
| `MAX_SUPPORT_MESSAGE` | **5 000** |
| `MAX_DESCRIPTION` | **2 000** |
| `MAX_JUSTIFICATION` | **500** |
| `MAX_EMAIL_LEN` | **254** (RFC 5321) |
| `MIN_PASSWORD` / `MAX_PASSWORD` | **12 / 256** (NIST 800-63B) |
| `MIN_TWO_FACTOR_CODE` / `MAX_TWO_FACTOR_CODE` | **6 / 6** |
| `MIN_ORG_SLUG_LEN` / `MAX_ORG_SLUG_LEN` | **2 / 32** |
| `MAX_WEBHOOK_URL_LEN` | **2 048** |
| `MAX_CALLBACK_URL_LEN` | **2 048** |
| `MAX_FILTER_INPUT` | **100** |
| **`MAX_POLICY_PATTERN_BYTES`** (ToolBlock pattern) | **4 096** (4 KiB) |
| **`MAX_WORKFLOW_DEPTH`** (sub-workflow chain depth) | **8** — the gate returns 422 beyond it |
| `MAX_DISPLAY_NAME` (XSS-guard) | **255** |
| `DEFAULT_MAX_RATE_LIMIT_RPM` (per-policy ceiling) | **1 000 000** (env `NULLRUN_POLICY_MAX_RATE_LIMIT_RPM`) |

### Approval-rule limits

| Setting | Value |
| --- | --- |
| `expires_in_seconds` default (DB) | **300 s** |
| Service clamp `[min..max]` | **30..=3 600** (1 min – 1 h) |
| `priority` bounds | `[0..=1 000]` (i16) |
| `action_label` max length | **200** |
| `VALID_RISK_LEVELS` | `["LOW","MEDIUM","HIGH"]` |
| `DEFAULT_RISK_LEVEL` | `"MEDIUM"` |
| **Per-org pending approvals cap** | **50** (env `NULLRUN_MAX_PENDING_APPROVALS_PER_ORG`, range 1–1 000) |
| Envelope TTL floor / ceiling | **60 s** / **86 400 s** (24 h) |
| `APPROVAL_ENVELOPE_GRACE_SECONDS` | **30** |
| `APPROVAL_CLOCK_SKEW_MARGIN_SECONDS` | **5** |
| Approval-rule predicate JSON byte cap | **Not supported** — only the typed schema validates shape |

### Reservation / chain TTLs

| Constant | Value |
| --- | --- |
| `DEFAULT_RESERVATION_TTL_SECONDS` | **300 s** (5 min) |
| `CHAIN_IDLE` | **300 s** |
| `CHAIN_REGISTERED` | **300 s** |
| `max_chain_duration_seconds` default | **3 600 s** (1 h) |
| `period_ttl_seconds` default | 3 600 × 24 × 30 = **30 days** |
| `EXECUTION_BINDING` TTL | **24 × 3 600 s** (24 h) |
| Heartbeat dedup marker | **35 s** |
| In-flight execution counter | **300 s** |

### Retention

| Constant | Value |
| --- | --- |
| `OUTBOX_DLQ_RETENTION_DAYS` | **30** |
| `DECISION_HISTORY_FALLBACK_DAYS` | **3** |
| `METERING_IDEMPOTENCY_WINDOW_DAYS` / `_SECONDS` | **30** / **2 592 000** |
| `METERING_EVENT_LOG_TTL_DAYS` / `_SECONDS` | **90** / **7 776 000** |
| `INGESTION_DLQ_RESOLVED_RETENTION_DAYS` | **7** |
| `INGESTION_DLQ_MAX_REPLAY_ATTEMPTS` | **5** |
| `INGESTION_DLQ_EXHAUSTED_RETENTION_DAYS` | **30** |
| `BILLING_DEAD_LETTER_RETENTION_DAYS` | **30** |

Per-tier decision-history retention:

| Plan | Decision history retention | Audit log |
|---|---|---|
| Lite | **3 d** | immutable on Growth+ only |
| Starter | **7 d** | immutable on Growth+ only |
| Growth | **30 d** | immutable |
| Scale | **90 d** | immutable |
| Enterprise | **unlimited** | immutable |

## Rate limits

### Edge / per-IP

| Layer | Default | Algorithm |
| --- | --- | --- |
| Per-IP edge | **60 RPM** token bucket (env `NULLRUN_IP_RATE_LIMIT_RPM`) | Token bucket; refill = max_rpm/60 |
| Per-IP edge bypass | operator-configurable kill-switch (fail-OPEN in dev only); bypass paths `/health`, `/metrics`, `/internal/*` | — |
| Per-IP edge multi-pod | shared counter store (fail-CLOSED on store error) | — |
| Per-IP edge response | 429 + `Retry-After` + `X-RateLimit-Limit/Remaining` | — |
| Auth endpoints | **5 req/min/IP** (`IpAuthRateLimiter::default`) | Token bucket (IP) + per-email counter |
| Email lockout | **5 failures → 300 s** lockout | — |

### Per-org / per-key

| Layer | Default | Algorithm |
| --- | --- | --- |
| Per-org aggregate | plan-driven per-org ceiling; global fixed capacity **10 000 RPM**; per-workspace fallback **1 000 RPM**; refill 100 tok/s | Token bucket (`PlanAwareRateLimiter`) |
| Per-org fallback (unknown org) | **5 RPM** — known hazard when the org cannot be resolved | — |
| Per-`(org, api_key)` | per-policy `limit`/`ttl_secs` (default `max_calls_per_minute × 60`) | **Fixed-window counter** (one atomic increment-and-expire step; NOT sliding) |
| Per-key fail-OPEN on store error | warn-and-fall-through, no wire code | — |
| Per-org aggregate fail-CLOSED on store error | **503**, `retry_after_seconds: 60` (surfaced to the SDK as `NR-R002`) | — |

The per-org aggregate rate limit is fail-CLOSED when the counter store
errors (returns 503), the per-key is fail-OPEN. This asymmetry is
intentional: a per-key miss only affects one key, but a per-org miss
would mask abuse.

## Per-plan limits

The unified budget check shares its `policies` and `approval_rules`
slots.

| Plan | workflows | tokens/hr | exec/mo | RPS | parallel | api_keys | seats | policies |
|---|---|---|---|---|---|---|---|---|
| **Lite** | **3** | **10 000** | **75 000** | **5** | **1** | **10** | **1** | **3** |
| **Starter** | **8** | **25 000** | **100 000** | **10** | **3** | **15** | **3** | **10** |
| **Growth** | **50** | **300 000** | **750 000** | **50** | **10** | **100** | **10** | **25** |
| **Scale** | **200** | unlimited | **2 000 000** | **300** | **50** | **350** | **75** | **150** |
| **Enterprise** | unlimited | unlimited | unlimited | **1 000** | **100** | unlimited | unlimited | unlimited |

## Wire-contract essentials

The gate emits `GateResponse` over HTTP 200/402/422/429/503. Key
fields:

- `execution_id` — server-minted **UUIDv7**. Client-supplied IDs are
  never honoured, so billing ownership is unambiguous and the
  identifier cannot be replayed.
- `projected_cost_cents` — **informational only**. The only
  enforcement-readable field is `remaining_budget_cents`.
- `cost_cents` on `/track` — server marks cost as `provisional` until
  reconciliation.
- `retry_after_ms` (top-level) — only present on `RATE_LIMIT_EXCEEDED`;
  milliseconds.
- `details.{retry_after_seconds, retry_after_ms}` — set on rate-limit
  and idempotency-unavailable responses.

**No `Retry-After` HTTP header on the gate path.** Body-only retry
hints. The header is emitted only by the per-IP edge middleware and
by `ApiError` on non-gate paths (429 → 30 s, 503 → explicit
`retry_after_seconds`).

**`X-NULLRUN-PROTOCOL`** is required on
`/api/v1/{gate,execute,track,track/batch,heartbeat,cancel,approvals/:id/consume}`.
Current=4, MIN=2, MAX=4; rejected at the protocol-version
middleware.

### Idempotency surfaces

| Endpoint | Mechanism | TTL | Outcome discriminator |
|---|---|---|---|
| `/api/v1/gate` | atomic insert-if-absent plus a conditional mutate; body field `operation_id` (NOT an `Idempotency-Key` header) | **24 h** | hit+match+Completed → 200 + `idempotent_replay:true`; hit+match+Pending → 409; hit+mismatch → 409; store down → 503 fail-CLOSED |
| `/api/v1/track` | same mechanism; body field `idempotency_key` | — | mismatch → 409; Completed → 200 + `idempotent_replay:true`; Pending → 409 + `retry_after_ms:500`; Failed → the record is wiped and the call falls through; store down → 503 |
| `/api/v1/cancel` | atomic insert-if-absent keyed on the execution id | 24 h | replay → 200 `{already_canceled:true}` |
| `/api/v1/heartbeat` | atomic insert-if-absent | 30 s | dedup |
| `/api/v1/approvals/:id/consume` | atomic row update flipping APPROVED→CONSUMED | — | 200 with `status: consumed\|already_consumed\|not_approved` |

**No use of the IETF `Idempotency-Key` header convention.** Drift from
any IETF-style clients — the header is silently ignored.

## Retry / backoff defaults

| Component | Settings |
| --- | --- |
| Slack alert delivery | `MAX_ATTEMPTS=3, BASE_BACKOFF_MS=1_000, MAX_BACKOFF_MS=30_000` (pure exponential, **no jitter**) |
| Litellm pricing cron | `PRICING_RETRY_MAX_ATTEMPTS=3` |
| Audit outbox | per-row 5-step exponential 1/2/4/8/16 s |
| Governance outbox | `max_attempts=3`, 30 s × 2^attempt + jitter |
| Notification outbox | `max_attempts=5`, 30 s × 2^attempt + jitter |
| Analytics outbox | `max_attempts=1` (fire-and-forget) |
| Detector retry | `retry.max_retries=5`, `retry.window_seconds=60` |

**No jitter** in the audit-outbox or Slack-alert retry loops. This is a
known limitation worth tracking if a thundering-herd pattern emerges.

## Gaps (honest)

These are the things we haven't measured in production. We list them
explicitly so technical buyers can ask the right questions during
evaluation.

### Verified absent

1. **OpenAI HTTP client has no timeout** — no connect, read,
   idle-pool, or TCP-keepalive setting.
2. **Anthropic / Google / Azure providers** — only the OpenAI
   provider is registered; `/api/v1/proxy*` is not wired into the
   live router.
3. **Provider retry** — rate-limited and unavailable provider errors
   are marked retryable but no caller retries; one outbound call, then
   return.
4. **`Retry-After` HTTP header on `/api/v1/proxy*` 502** — bare status,
   no header, no JSON envelope.
5. **OpenAI `429` retry hint** — the hardcoded 60 s value is
   **dropped on the floor**, never emitted as `Retry-After`.
6. **No per-call timeout** on counter-store script or command
   execution — only a 5 s *connection* timeout; no per-call timeout
   wrapper.
7. **No automatic retry** in the gate/track handlers.
8. **No jitter in any retry loop** — Slack alerts (1 s → 30 s), pricing
   cron, audit outbox, governance outbox. Pure exponential only.
9. **No server-side tool-execution timeout on `/execute`** — SDK runs
   the tool locally; the server has no watchdog.
10. **No client-initiated cancellation of in-flight `/gate` or
    `/execute`** — no DELETE/HEAD routes are registered;
    `/cancel` is the only de-facto abort (separate call).
11. **No server-side deadline on `/execute` independent of `/gate`** —
    only the budget-store breaker fail-fast at `/execute`.
12. **WS idle timeout** — 30 s ping is a probe, not an
    idle-disconnect policy; a silent client stays connected.
13. **WS per-org connection cap** — `MAX_SSE_PER_ORG=5` exists; WS has
    no equivalent cap.
14. **WS max frame size / max message size** — no
    `max_frame_size`/`max_message_size` override; axum defaults apply.
15. **`WS_PING_INTERVAL` / `WS_RECONNECT_MAX` env var** — not
    configurable.
16. **State-store audit-outbox queue depth cap** — only a per-row retry
    cap (5) then dead-letter; no global cap.
17. **Explicit concurrency cap on the audit-outbox drain** — only a
    consecutive-error cap of 5 per tick break.
18. **Key-count cap on the reservation scan script** — only the
    256-iteration cap exists; the consume-side script has no scan /
    time-bound.
19. **Approval-rule predicate JSON byte cap** — a free-form JSON value
    only, no byte validator.
20. **Stripe webhook** — not supported; Polar is the sole payment
    provider.
21. **`X-RateLimit-Limit` / `X-RateLimit-Remaining` / `X-RateLimit-Reset`
    on gate path** — emitted only by the per-IP edge rate-limit
    middleware.
22. **`Retry-After` HTTP header on gate** — gate uses body
    `retry_after_ms` / `retry_after_seconds` only.
23. **Auth-class gate error variants** — the typed registry carries
    only a revoked-key code; missing, invalid, and expired keys flow
    through the generic error envelope.
24. **The in-flight idempotency code on `/track`** is emitted inline on
    the track path but is not one of the typed gate error variants — a
    drift from inline emission.

### Not measured (would require load test)

1. Real p99 RTT to the budget store at production scale for the
   reservation worst case (256 scan iterations + 256 bulk reads).
2. Worst-case first-request latency on a budget-store partition
   before the breaker trips (5 consecutive × 10 s acquire ≈ 50 s
   before short-circuit).
3. OpenAI upstream hung-socket behavior in practice — the outer 30 s
   request timeout is the only bound; no per-call connect timeout.
4. WS reconnect storms — no server-side cap; SDK could reconnect
   indefinitely under split-brain.
5. State-store pool contention under `/track` bursts — the bounded
   ingestion queue holds 10 000 events, drops the oldest above 9 000,
   and drops at a hard cap of 15 000, but actual write throughput is
   not measured.

### Drift between the OpenAPI contract and the server

1. **`GateResponse` in the published OpenAPI contract** is missing
   wire fields the server actually returns: `approval_id`,
   `approval_timeout_seconds`, `approval_expires_at`, `execution_id`,
   `retry_after_ms`, `idempotent_replay`, `operation_id`,
   `decision_context`, `details`. The OpenAPI contract declares
   itself canonical; the server is wire-true.
2. **`/check`** — returns 410 GONE, but the OpenAPI contract may
   still document it as active.

## See also

- [Circuit breaker](../concepts/circuit-breaker.md) — what the agent
  sees when a failure occurs
- [Error handling](../concepts/error-handling.md) — wire code → exception
  mapping
- [Budgets](../concepts/budgets.md) — budget reserve/consume semantics
- [API keys](../concepts/api-keys.md) — HMAC, rotation, drain
- [Control plane](../concepts/control-plane.md) — WebSocket keepalive
- [HTTP API → Capabilities](../reference/http-api.md#capabilities) —
  protocol version + `/health` `min`/`max`
- [Compliance](../compliance/index.md) — data-handling posture
