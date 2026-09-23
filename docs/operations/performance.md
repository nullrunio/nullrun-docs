---
title: Performance & limits
maturity: stable
description: Latency budgets, failure-mode behaviour, integration limits, and timeout handling — for technical buyers evaluating NULLRUN.
---

# Performance & limits

A consolidated reference for technical buyers evaluating NULLRUN's
operational characteristics. Every value below is anchored to backend
code with `file:line` citations; rows marked **Not measured** are honest
gaps — we surface what we don't know rather than quote a number we
haven't earned.

This page is the load-bearing complement to the
[Circuit breaker](../concepts/circuit-breaker.md) and
[Error handling](../concepts/error-handling.md) concept pages:
those explain the *what* and *why*, this page enumerates the
*bounds*.

## Hot-path latency

The gate hot path is **`/api/v1/gate`** → Redis Lua (reserve_v3) →
Postgres audit outbox. Wall-clock budgets are layered; the inner cap
is the binding one.

| Stage | Bound | Source |
|---|---|---|
| Outer HTTP request (`/api/v1/*`) | **30 s** (env `REQUEST_TIMEOUT_SECS`, default 30) | `backend/src/proxy/server.rs:99-106,326,362` — tower-http `TimeoutLayer` |
| `/api/v1/gate` inner hard timeout | **5 s** (`GATE_HANDLER_HARD_TIMEOUT`) | `backend/src/proxy/http/gate/gate.rs:636-662` — on expiry returns 402 `BUDGET_REDIS_UNAVAILABLE` |
| Gate orchestrator inner hard timeout | **3 s** (`ORCHESTRATOR_HARD_TIMEOUT`) | `backend/src/proxy/http/gate/internal.rs:2265-2266` — on expiry returns 402 + `redis_unavailable_inc("gate_timeout")` |
| `/api/v1/execute` inner timeout | **None** — relies on outer 30 s + Redis breaker fail-fast (<100 ms once tripped) | `backend/src/proxy/http/gate/execute.rs:66-386` |
| `/api/v1/track` inner timeout | **None** — relies on outer 30 s | `backend/src/proxy/handlers.rs:5234` |
| `reserve_v3.lua` SCAN loop cap | **256 iterations** (`MAX_SCAN_ITERATIONS`, raised from 16 by NR-073) | `backend/src/redis/scripts/reserve_v3.lua:508` |
| `reserve_v3.lua` SCAN `COUNT` per iter | **1 000** (256 k slot visits worst case) | `reserve_v3.lua:521` |
| `RESERVED_SCANNED_PARTIAL` return | typed `{-1, "RESERVED_SCANNED_PARTIAL", reserved, projected}` — fail-CLOSED 402, never silent truncation | `reserve_v3.lua:558-570` |
| Redis pool `wait_timeout` | **5 000 ms** (env `REDIS_POOL_TIMEOUT_MS`) | `backend/src/redis/pool.rs:153,321` |
| Redis pool `create_timeout` | **10 s** (env `REDIS_ACQUIRE_TIMEOUT`, clamp 1–60 s) | `backend/src/redis/pool.rs:154,323` |
| Redis pool `max_size` | **32** (env `REDIS_POOL_MAX_SIZE`) | `backend/src/redis/pool.rs:152,320` |
| Postgres pool `acquire_timeout` | **10 s** | `backend/src/db/mod.rs:1641` |
| Postgres `statement_timeout` (per-connection) | **30 000 ms** (env `NULLRUN_DB_STATEMENT_TIMEOUT_MS`) | `backend/src/db/mod.rs` GUC setup |

### Healthy-path budget

When Redis is healthy and no `/check` style fan-out is required:

1. Network RTT to Redis: sub-millisecond within a region.
2. `reserve_v3.lua` single atomic step: <5 ms typical, <50 ms at p99.
3. Orchestrator evaluation: <2 ms typical.
4. Total `/api/v1/gate` server-side: **<10 ms typical, <60 ms p99**.

The 3 s orchestrator cap is the binding inner budget; the 5 s gate
handler cap is a one-above safety net. The 30 s outer `TimeoutLayer`
should never fire on a healthy Redis.

### First-burst (breaker not yet tripped)

If Redis is reachable but slow, the worst case before the breaker
trips is:

- 1 acquire × 10 s + 1 wait × 5 s + 1 SCAN cap × ~50 ms ≈ **up to 15 s**
- On the 5th consecutive failure, the breaker trips and subsequent
  calls short-circuit **sub-100 ms** returning
  `BUDGET_REDIS_UNAVAILABLE` (see [Redis failure](#redis-failure) below).

### Not measured

- Real Redis p99 RTT at production scale for the worst-case
  `reserve_v3.lua` path (256 SCAN + 256 MGET ≈ 512 commands).
- Worst-case first-request latency on a Redis partition before the
  breaker trips.

## Behaviour when a service is unavailable

Every enforcement-path failure mode below is **fail-CLOSED** unless
explicitly noted. The default posture is "do not let the agent proceed
when an enforcement signal is missing".

### Redis failure

The Redis circuit breaker has three profiles, picked by call-site:

| Profile | `failure_threshold` | `recovery_timeout_ms` | `half_open_max_probes` | Used for |
|---|---|---|---|---|
| **default** | 5 | 30 000 (30 s) | 1 | Generic Redis paths |
| **`critical()`** | 3 | 60 000 (60 s) | 1 | Budget enforcement on the gate hot path (FailClosed) |
| **`high_traffic()`** | 20 | 10 000 (10 s) | 3 | Buffered / StaleCache / analytics paths |

Source: `backend/src/redis/breaker/config.rs:29-80`.

The breaker short-circuits in **sub-100 ms** once OPEN (`execute_with_degraded`
returns `CircuitOpen` for `FailClosed`/`Buffered` profiles).

| Wire `error_code` | HTTP | Triggered by | Source |
|---|---|---|---|
| `BUDGET_REDIS_UNAVAILABLE` | **402** | reserve_v3 Lua failure / inline Redis fail on gate path | `error_codes.rs:616`; `gate.rs:657`; `internal.rs:4241-4267` |
| `RATE_LIMIT_REDIS_UNAVAILABLE` | **503** | per-org aggregate bucket Redis fail (fail-CLOSED) | `error_codes.rs:739`; `orchestrator.rs:671-682,713` |
| `IDEMPOTENCY_REDIS_UNAVAILABLE` | **503** | `IdempotencyStore` Redis fail (fail-CLOSED) | `error_codes.rs:741`; `gate.rs:484,546,563,585,603` |
| `WORKFLOW_DEPTH_LOOKUP_FAILED` | **503** | ADR-036 cycle-walk Redis fail | `error_codes.rs:754` |
| `INVOKE_PERSIST_FAILED` | **503** | ADR-036 invoke persist fail | `error_codes.rs:755` |
| `REDIS_UNAVAILABLE` (inline) | varied | inline pre-check on `/track` idempotency | `handlers.rs:5318`; `orchestrator.rs:1265` |

**Retry behaviour:** no automatic Redis retry in
reservation/consume/idempotency handlers — failures surface directly to
the breaker. The breaker is the retry mechanism.

**Lua return-code → HTTP mapping (exhaustive):**

| Lua return | Outcome | `error_code` | HTTP |
|---|---|---|---|
| `HARD_BUDGET_EXCEEDED` | Hard block | `BUDGET_HARD_BLOCKED` | 402 |
| `ORG_BUDGET_EXCEEDED` | Org ceiling | `BUDGET_ORG_CEILING_BLOCKED` | 402 |
| `WORKFLOW_BUDGET_EXCEEDED` | Workflow | `BUDGET_WORKFLOW_BLOCKED` | 402 |
| `SOFT_OVERDRAFT_CAP` | Overdraft cap hit | `BUDGET_OVERDRAFT_EXCEEDED` | 402 |
| `RESERVED_CAP_EXCEEDED` | Anti-DoS reserved | `BUDGET_ANTI_DOS_RESERVED_CAP` | 402 |
| `RESERVED_SCANNED_PARTIAL` | NR-015 partial scan | `RESERVED_SCANNED_PARTIAL` | 402 |
| `BUDGET_EXCEEDED` (consume-side) | Consume-side | `BUDGET_EXCEEDED` | **429 + `Retry-After: 1`** |
| `CONSUME_OVERBUDGET` | Consume overshoot | `CONSUME_OVERBUDGET` | **422** |
| `RESERVATION_NOT_FOUND` | TTL expired / orphan | `RESERVATION_NOT_FOUND` | 503 |
| `POLICY_UNCONFIGURED` | Invariant break | `POLICY_UNCONFIGURED` | 500 |

### Postgres failure

| Setting | Value | Source |
|---|---|---|
| Pool `max_connections` | `(num_cpus::get().min(12) * 2 + 10)` (≈25–34 on 12-core); env `DATABASE_MAX_CONNECTIONS` | `backend/src/db/mod.rs:1637-1641` |
| Pool `idle_timeout` | **600 s** | same |
| Pool `max_lifetime` | **1 800 s** (DNS / PgBouncer rollover protection) | same |
| `idle_in_transaction_session_timeout` | **60 000 ms** | same |
| DB circuit breaker profile | mirrors Redis default (5 / 30 s) | `backend/src/db_breaker.rs` |
| Breaker short-circuit on OPEN | **<100 ms** returns `CircuitError::CircuitOpen` | same |

#### `/track` outbox path (the only enforcement-side PG write)

The audit-row INSERT is **best-effort and off the request path**:

- Wrapper: `PostgresCircuitBreaker::global()` with `FailureMode::Degraded`
  (`backend/src/proxy/http/gate/internal.rs:4029`).
- On INSERT error: `tracing::warn!` + `postgres_metrics.record_connection_error()`
  + **continue** — the gate response is unchanged. The audit row is
  not on the critical path.
- Drain location: `backend/src/outbox/audit_drain.rs`, spawned via fast
  ticker at `main.rs:3212`.
- Drain tick interval: **5 s** default (env `OUTBOX_AUDIT_DRAIN_INTERVAL_SECONDS`,
  clamp 2–300).
- Per-tick batch size: **100**.
- Per-tick timeout: **30 s**.
- Per-row backoff: **1 / 2 / 4 / 8 / 16 s** exponential (CLAUDE.md §15).
- `MAX_CONSECUTIVE_ERRORS` per tick: **5** (tick break on persistent DB errors).
- DLQ at `retry_count >= 5`: hard ceiling.
- `mark_immediate_dead_letter` for permanent failures: v3.76 P0-3.
- Retention once DLQ'd: **30 days** (`OUTBOX_DLQ_RETENTION_DAYS`,
  `backend/src/retention.rs:40`).

#### Other outbox partitions

| Partition | `max_attempts` | Backoff base |
|---|---|---|
| governance | **3** | 30 s × 2^attempt + jitter |
| notification | **5** | 30 s × 2^attempt + jitter |
| analytics | **1** (fire-and-forget) | — |

### Upstream LLM / provider failure

The provider module is sparse — only `OpenAIProvider` is registered
(`backend/src/proxy/provider/mod.rs:264-269`; Anthropic / Google / Azure
types are documented but commented out, and `/api/v1/proxy*` is not
wired into `routes.rs`).

| Thing | Value | Source |
|---|---|---|
| OpenAI `reqwest::Client` timeout | **Not configured** — no `.timeout()`, `.connect_timeout()`, `.read_timeout()`, `.pool_max_idle_per_host`, `.tcp_keepalive` | `backend/src/proxy/provider/openai.rs:16,25` |
| Provider retry | **None** — one `.send()` per call, immediate return | `backend/src/proxy/provider/openai.rs:122-126,144,194,226` |
| HTTP status on provider failure | bare `502 BAD_GATEWAY` — no `error_code`, no `Retry-After`, no JSON envelope | `backend/src/proxy/http/proxy.rs:109-112` |
| OpenAI `429` parse | `ProviderError::RateLimited(60)` — the **60 s hint is dropped on the floor** (never emitted as `Retry-After`) | `backend/src/proxy/provider/openai.rs:130-141` |
| Streaming failure shape | `governance_events` carries `control_decision: e.to_string()` but HTTP status stays 200 | `backend/src/proxy/http/proxy.rs:300,340-349` |

This is the area with the **largest gap** between SDK promise and
backend reality. Practical implication: a hung OpenAI socket stalls
until the outer 30 s `TimeoutLayer` fires; there is no per-call
connect timeout, no retry, and no machine-readable error envelope.

### Geo / sanctions failure

| Setting | Value | Source |
|---|---|---|
| `SANCTIONED` jurisdictions | RU, IR, KP, SY, CU, BY, VE, MM, AF | `backend/src/proxy/middleware/geo_block.rs:64-74` |
| `HIGH_RISK_NO_SERVICE` jurisdictions | EU-27 + EEA + UK + CH + CN + IN | `geo_block.rs:76-86` |
| `BlockSanctioned` arm | 403 + `{error:"service_unavailable_in_jurisdiction", message, fortress_reason:"sanctions"}` + headers `X-Fortress-Block-Country` + `X-Fortress-Block-Reason: sanctions` | `geo_block.rs:714-758` |
| `BlockHighRisk` arm | 403 (or **503** if GeoIP DB unavailable) + same shape | `geo_block.rs:759-806` |
| GeoIP DB missing / unreadable | **All ingress rejected (503)** — fail-CLOSED by design | `geo_block.rs:33-36,138-149,279-281` |
| `NULLRUN_GEOBLOCK_DISABLED` | dev-only fail-OPEN escape (logs WARN) | `geo_block.rs:457-466,585-608` |
| Sanctions SDN CSV missing | 6-entry hand-curated fallback (fail-OPEN with WARN) | `backend/src/proxy/middleware/sanctions.rs:185-221` |
| `NULLRUN_SANCTIONS_SCREENING_DISABLED` | operator kill-switch (fail-OPEN) | `sanctions.rs:322-330` |

See [Geo restrictions](../compliance/geo-restrictions.md) and
[Sanctions screening](../compliance/sanctions-screening.md) for the
full compliance contract.

## Timeouts and integration limits

### HTTP / WebSocket / SSE

| Surface | Setting | Value | Source |
|---|---|---|---|
| `/api/v1/*` outer request | tower-http `TimeoutLayer` | **30 s** | `proxy/server.rs:99-106` |
| HMAC re-read cap (`MAX_BODY_SIZE`) | body cap before HMAC verify | **10 MiB** | `proxy/middleware/hmac_verify.rs:73` |
| WebSocket server ping interval | `Message::Ping(vec![])` | **30 s** | `proxy/http/ws_control.rs:983-984` |
| WebSocket HMAC replay window | `WS_HMAC_MAX_AGE_SECONDS` | **300 s** | `ws_control.rs:37,1094` |
| WebSocket idle disconnect | **None** — closed only on Close frame / stream error / send failure | — | `ws_control.rs:935-948` |
| WebSocket per-org connection cap | **None** (SSE has `MAX_SSE_PER_ORG=5`) | — | — |
| WebSocket max frame / message size | **None configured** — axum defaults apply | — | — |
| SSE max connection duration | hard cap | **24 h** | `proxy/http/stream.rs:54` |
| SSE JSON heartbeat cadence | informational heartbeat | **30 s** | `stream.rs:78,421-422` |
| SSE protocol-level keepalive (axum `KeepAlive`) | text `"ping"` | **15 s** | `stream.rs:508-512` |
| SSE per-org concurrent cap | `MAX_SSE_PER_ORG` | **5** | `proxy/http/sse_limiter.rs:44` |
| EventBus default capacity | bounded queue | **4 096 events** (overflow at **3 072 / 75%**) | `proxy/http/event_bus.rs:881-887` |
| Slow-consumer signal | server emits `WsMessage::ResyncRequired` to force SDK reconnect | — | `ws_control.rs:967-974` |

### OAuth / webhook clients (cold path)

| Client | Timeout | Source |
|---|---|---|
| GitHub OAuth | `.timeout(10s).connect_timeout(5s)` | `auth/github.rs:102-104,149-151,190-192,237-239,288-290` |
| Google OAuth | `.timeout(10s).connect_timeout(5s)` | `auth/google.rs:314-316,372-374,416-418,470-472` |
| SSO | `.timeout(10s).connect_timeout(5s)` | `auth/sso.rs:423-424` |
| Cron egress (litellm pricing) | `.timeout(10s).connect_timeout(5s)` | `cron.rs:1272-1274` |
| Slack `chat.postMessage` | `.timeout(10s)` (no separate connect timeout) | `main.rs:1510-1513` |

### HMAC policy

| Setting | Value | Source |
|---|---|---|
| `NULLRUN_HMAC_REQUIRED` default | `false` (warns at runtime) | `config.rs:166` |
| `NULLRUN_HMAC_MAX_AGE_SECS` default | **300 s** | `config.rs:171` |
| `NULLRUN_CONSUME_RACE_WINDOW_SECONDS` default | **2 s**, clamped `[0..30]` | `config.rs:222-226` |
| HMAC-verified SDK paths | `["/api/v1/check", "/api/v1/execute", "/api/v1/gate", "/api/v1/track", "/api/v1/track/batch"]` | `proxy/middleware/hmac_verify.rs:138-144` |
| Gateway signing key min length | **32 bytes** (env `NULLRUN_GATEWAY_SIGNING_KEY`) | `config.rs:38-42` |

### Webhook signature replay windows

| Webhook | Algorithm | Replay window | Source |
|---|---|---|---|
| Slack Events | HMAC-SHA256 over `v0:{ts}:{raw_body}`, header `X-Slack-Signature: v0=<hex>` | **300 s** | `slack_oauth.rs:820-823,1295-1328`; replay `:1319` |
| Slack OAuth state | TTL | **600 s** | `slack_oauth.rs:71` `STATE_TTL_SECS` |
| Slack install ticket | TTL | **300 s** | `slack_oauth.rs:80` `INSTALL_TICKET_TTL_SECS` |
| Polar | Stripe-shaped `t=<unix>,v1=<hex>` over `timestamp.payload`, HMAC-SHA256, raw bytes | **300 s** | `billing/polar.rs:21,160-200` `WEBHOOK_SIGNATURE_MAX_AGE_SECS` |
| Polar sandbox | `is_sandbox() == true` skips verification | — | `billing/polar.rs:155-157` |
| Stripe | **Not in code** — Polar is the sole payment provider | — | — |

## Hard limits and caps

### Body / payload caps

| Cap | Value | Source |
|---|---|---|
| HTTP request body cap | **10 MiB** (`10 * 1024 * 1024`) | `proxy/server.rs:363` `RequestBodyLimitLayer::new(...)` |
| MCP discovery SSE chunk | **65 536 bytes** (64 KiB) | `proxy/http/mcp/discovery_probe.rs:498,772` |

### Validation caps (`validation_constants.toml` — single source of truth, generated by `build.rs`)

| Constant | Value | Source |
|---|---|---|
| `MAX_WORKFLOW_NAME` | **80** | `validation_constants.toml:17` |
| `MAX_POLICY_NAME` | **80** | `:18` |
| `MAX_API_KEY_NAME` | **80** | `:19` |
| `MAX_ORG_NAME` | **100** | `:20` |
| `MAX_ALERT_RULE_NAME` | **80** | `:21` |
| `MAX_KILL_REASON` | **500** | `:24` |
| `MAX_SUPPORT_MESSAGE` | **5 000** | `:25` |
| `MAX_DESCRIPTION` | **2 000** | `:26` |
| `MAX_JUSTIFICATION` | **500** | `:27` |
| `MAX_EMAIL_LEN` | **254** (RFC 5321) | `:30` |
| `MIN_PASSWORD` / `MAX_PASSWORD` | **12 / 256** (NIST 800-63B) | `:31-32` |
| `MIN_TWO_FACTOR_CODE` / `MAX_TWO_FACTOR_CODE` | **6 / 6** | `:33-34` |
| `MIN_ORG_SLUG_LEN` / `MAX_ORG_SLUG_LEN` | **2 / 32** | `:37-38` |
| `MAX_WEBHOOK_URL_LEN` | **2 048** | `:39` |
| `MAX_CALLBACK_URL_LEN` | **2 048** | `:40` |
| `MAX_FILTER_INPUT` | **100** | `:43` |
| **`MAX_POLICY_PATTERN_BYTES`** (ToolBlock pattern) | **4 096** (4 KiB) | `:46` |
| **`MAX_WORKFLOW_DEPTH`** (sub-workflow chain, ADR-036) | **8** | `:57`; gate at `orchestrator.rs:4228` → 422 `WORKFLOW_DEPTH_EXCEEDED` |
| `MAX_DISPLAY_NAME` (XSS-guard) | **255** | `validation.rs:214` |
| `DEFAULT_MAX_RATE_LIMIT_RPM` (per-policy ceiling) | **1 000 000** (env `NULLRUN_POLICY_MAX_RATE_LIMIT_RPM`) | `validation.rs:223` |

### Approval-rule limits

| Setting | Value | Source |
|---|---|---|
| `expires_in_seconds` default (DB) | **300 s** | `db/mod.rs:8069` |
| Service clamp `[min..max]` | **30..=3 600** (1 min – 1 h) | `approval_rule_service.rs:55-56` |
| `priority` bounds | `[0..=1 000]` (i16) | `approval_rule_service.rs:49-50` |
| `action_label` max length | **200** | `:60` |
| `VALID_RISK_LEVELS` | `["LOW","MEDIUM","HIGH"]` | `:68` |
| `DEFAULT_RISK_LEVEL` | `"MEDIUM"` | `:73` |
| **Per-org pending approvals cap** | **50** (env `NULLRUN_MAX_PENDING_APPROVALS_PER_ORG`, range 1–1 000) | `redis/mod.rs:530` `MAX_PENDING_APPROVALS_PER_ORG`; 429 `TOO_MANY_PENDING_APPROVALS` on overflow |
| Envelope TTL floor / ceiling | **60 s** / **86 400 s** (24 h) | `redis/mod.rs:515,521` |
| `APPROVAL_ENVELOPE_GRACE_SECONDS` | **30** | `redis/mod.rs:498` |
| `APPROVAL_CLOCK_SKEW_MARGIN_SECONDS` | **5** | `redis/mod.rs:509` |
| Approval-rule predicate JSON byte cap | **Not in code** — only typed schema validates shape | — |

### Reservation / chain TTLs

| Constant | Value | Source |
|---|---|---|
| `DEFAULT_RESERVATION_TTL_SECONDS` | **300 s** (5 min) | `cost/reservation.rs:48`; `cost/registry.rs:76` `RESERVATION_TTL_SECONDS = 300` |
| `CHAIN_IDLE` | **300 s** | `redis/mod.rs:553`; `consume_v3.lua:597` |
| `CHAIN_REGISTERED` | **300 s** | `redis/mod.rs:559` |
| `max_chain_duration_seconds` default | **3 600 s** (1 h) | `enforcement/unified_evaluator.rs:151,605,809`; DB `MAX_CHAIN_DURATION_SECONDS INTEGER NOT NULL DEFAULT 3600` (`db/mod.rs:7525`) |
| `period_ttl_seconds` default | 3 600 × 24 × 30 = **30 days** | `enforcement/unified_evaluator.rs:152` |
| `EXECUTION_BINDING` TTL | **24 × 3 600 s** (24 h) | `redis/mod.rs:549` |
| Heartbeat dedup marker | **35 s** | `redis/mod.rs:303-304` |
| `in_flight` counter | **300 s** | `redis/mod.rs:317-322` |

### Retention (`backend/src/retention.rs` — single source of truth)

| Constant | Value | Source |
|---|---|---|
| `OUTBOX_DLQ_RETENTION_DAYS` | **30** | `retention.rs:40` (CLAUDE.md §15) |
| `DECISION_HISTORY_FALLBACK_DAYS` | **3** | `retention.rs:59` |
| `METERING_IDEMPOTENCY_WINDOW_DAYS` / `_SECONDS` | **30** / **2 592 000** | `retention.rs:76,80` |
| `METERING_EVENT_LOG_TTL_DAYS` / `_SECONDS` | **90** / **7 776 000** | `retention.rs:94,98` |
| `INGESTION_DLQ_RESOLVED_RETENTION_DAYS` | **7** | `retention.rs:118` |
| `INGESTION_DLQ_MAX_REPLAY_ATTEMPTS` | **5** | `retention.rs:139` |
| `INGESTION_DLQ_EXHAUSTED_RETENTION_DAYS` | **30** | `retention.rs:158` |
| `BILLING_DEAD_LETTER_RETENTION_DAYS` | **30** | `retention.rs:173` |

Per-tier retention (`decision_history_retention.rs:14-21`):

| Plan | Decision history retention | Audit log |
|---|---|---|
| Lite | **3 d** | immutable on Growth+ only |
| Starter | **7 d** | immutable on Growth+ only |
| Growth | **30 d** | immutable |
| Scale | **90 d** | immutable |
| Enterprise | **unlimited** | immutable |

## Rate limits

### Edge / per-IP

| Layer | Default | Algorithm | Source |
|---|---|---|---|
| Per-IP edge | **60 RPM** token bucket (env `NULLRUN_IP_RATE_LIMIT_RPM`) | Token bucket; refill = max_rpm/60 | `proxy/middleware/ip_rate_limit.rs:168-174` |
| Per-IP edge bypass | env `NULLRUN_IP_RATE_LIMIT_DISABLED=1`; bypass paths `/health`, `/metrics`, `/internal/*` | — | same |
| Per-IP edge multi-pod | Redis-backed via `NULLRUN_IP_RATE_LIMIT_REDIS_URL` (fail-CLOSED) | — | same |
| Per-IP edge response | 429 + `Retry-After` + `X-RateLimit-Limit/Remaining` | — | same |
| Waitlist (high-risk jurisdictions) | **5 submissions/hour/IP** (env `NULLRUN_WAITLIST_PER_HOUR`); window 3 600 s | Counter | `ip_rate_limit.rs:536-648`; 429 `WAITLIST_RATE_LIMITED` |
| Auth endpoints | **5 req/min/IP** (`IpAuthRateLimiter::default`) | Token bucket (IP) + per-email counter | `proxy/middleware/auth_rate_limit.rs:183-185,318-321` |
| Email lockout | **5 failures → 300 s** lockout | — | same |

### Per-org / per-key

| Layer | Default | Algorithm | Source |
|---|---|---|---|
| Per-org aggregate | plan-driven `max_rpm` from `plans.limits.max_rps × 60`; global fixed capacity **10 000 RPM**; per-workspace fallback **1 000 RPM**; refill 100 tok/s | Token bucket (`PlanAwareRateLimiter`) | `proxy/middleware/rate_limit.rs:137-138,148-184` |
| Per-org fallback (unknown org) | **5 RPM** — bug-class hazard, surfaces in tests | — | `rate_limit.rs:199` |
| Per-`(org, api_key)` Redis | per-policy `limit`/`ttl_secs` (default `max_calls_per_minute × 60`); key shape `ratelimit:org:{org_id}:key:{key_id}` | **Fixed-window counter** (atomic GET→INCR→EXPIRE in Lua; NOT sliding) | `redis/scripts/check_rate_limit_v1.lua:16-17,50-52,58-80` |
| Per-key fail-OPEN on Redis error | warn-and-fall-through, no wire code | — | `proxy/http/gate/orchestrator.rs` (per-key branch) |
| Per-org aggregate fail-CLOSED on Redis error | **503** `RATE_LIMIT_REDIS_UNAVAILABLE`, `retry_after_seconds: 60` | — | `orchestrator.rs:671-682,713` |

The per-org aggregate rate limit is fail-CLOSED on Redis error (returns
503), the per-key is fail-OPEN. This asymmetry is intentional: a
per-key miss only affects one key, but a per-org miss would mask
abuse.

## Per-plan limits

Seeded in `002_plans.sql`; unified budget
(`admission/limit_checks.rs:1013-1076`) shares `policies +
approval_rules` slots (drift-pinned by migration 332).

| Plan | workflows | tokens/hr | exec/mo | RPS | parallel | api_keys | seats | policies |
|---|---|---|---|---|---|---|---|---|
| **Lite** | **3** | **10 000** | **75 000** | **5** | **1** | **10** | **1** | **3** |
| **Starter** | **8** | **25 000** | **100 000** | **10** | **3** | **15** | **3** | **10** |
| **Growth** | **50** | **300 000** | **750 000** | **50** | **10** | **100** | **10** | **25** |
| **Scale** | **200** | unlimited | **2 000 000** | **300** | **50** | **350** | **75** | **150** |
| **Enterprise** | unlimited | unlimited | unlimited | **1 000** | **100** | unlimited | unlimited | unlimited |

## Wire-contract essentials

The gate emits `GateResponse` over HTTP 200/402/422/429/503. Key
fields (`backend/src/proxy/http/gate/internal.rs:551-734`):

- `execution_id` — server-minted **UUIDv7**. Client-supplied IDs are
  never honoured (ADR-003 — ownership-ambiguous billing + replay
  attack surface).
- `projected_cost_cents` — **informational only**. The only
  enforcement-readable field is `remaining_budget_cents`.
- `cost_cents` on `/track` — server marks cost as `provisional` until
  reconciliation.
- `retry_after_ms` (top-level) — only present on `RATE_LIMIT_EXCEEDED`;
  milliseconds.
- `details.{retry_after_seconds, retry_after_ms}` — set on rate-limit
  and idempotency-unavailable responses.

**No `Retry-After` HTTP header on the gate path.** Body-only retry
hints. The header is emitted only by `ip_rate_limit` middleware and
by `ApiError` on non-gate paths (429 → 30 s, 503 → explicit
`retry_after_seconds`).

**`X-NULLRUN-PROTOCOL`** is required on
`/api/v1/{gate,execute,track,track/batch,heartbeat,cancel,approvals/:id/consume}`.
Current=4, MIN=2, MAX=4 (`protocol.rs:67-71`); rejected at middleware
`protocol_version_middleware` (`protocol.rs:297-330`).

### Idempotency surfaces

| Endpoint | Mechanism | TTL | Outcome discriminator |
|---|---|---|---|
| `/api/v1/gate` | `IdempotencyStore` (atomic SETNX + Lua mutate); body field `operation_id` (NOT `Idempotency-Key` header) | **24 h** (`GATE_TTL_SECONDS`, `gate.rs:523`) | hit+match+Completed → 200 + `idempotent_replay:true`; hit+match+Pending → 409 `IDEMPOTENCY_REDIS_UNAVAILABLE`; hit+mismatch → 409 `IDEMPOTENCY_KEY_MISMATCH`; Redis down → 503 fail-CLOSED |
| `/api/v1/track` | `IdempotencyStore` reused; body field `idempotency_key` | — | mismatch → 409 `IDEMPOTENCY_KEY_MISMATCH`; Completed → 200 + `idempotent_replay:true`; Pending → 409 `IDEMPOTENCY_IN_FLIGHT` + `retry_after_ms:500`; Failed → wipe via `delete` + fall through; Redis down → 503 |
| `/api/v1/cancel` | `SETNX cancel:{execution_id}` | 24 h | replay → 200 `{already_canceled:true}` |
| `/api/v1/heartbeat` | `SETNX` | 30 s | dedup |
| `/api/v1/approvals/:id/consume` | SQL-layer atomic UPDATE flipping APPROVED→CONSUMED (ADR-047) | — | 200 with `status: consumed\|already_consumed\|not_approved` |

**No use of the IETF `Idempotency-Key` header convention.** Drift from
any IETF-style clients — the header is silently ignored.

## Retry / backoff defaults

| Component | Settings | Source |
|---|---|---|
| Slack alert delivery | `MAX_ATTEMPTS=3, BASE_BACKOFF_MS=1_000, MAX_BACKOFF_MS=30_000` (pure exponential, **no jitter**) | `alert/providers.rs:184-186` |
| Litellm pricing cron | `PRICING_RETRY_MAX_ATTEMPTS=3` | `cron.rs:998` |
| Audit outbox | per-row 5-step exponential 1/2/4/8/16 s | `outbox/audit_drain.rs` |
| Governance outbox | `max_attempts=3`, 30 s × 2^attempt + jitter | `outbox/partitions.rs` |
| Notification outbox | `max_attempts=5`, 30 s × 2^attempt + jitter | same |
| Analytics outbox | `max_attempts=1` (fire-and-forget) | same |
| Detector retry | `retry.max_retries=5`, `retry.window_seconds=60` | `config.rs:665-666` |

**No jitter** in the audit-outbox or Slack-alert retry loops. This is a
known limitation worth tracking if a thundering-herd pattern emerges.

## Gaps (honest)

These are the things we either couldn't find in the code or didn't
measure in production. We list them explicitly so technical buyers can
ask the right questions during evaluation.

### Not in code (verified absent)

1. **OpenAI `reqwest::Client` has no timeout** — no `.timeout()`,
   `.connect_timeout()`, `.read_timeout()`, `.pool_max_idle_per_host`,
   `.tcp_keepalive` (`backend/src/proxy/provider/openai.rs:25`).
2. **Anthropic / Google / Azure providers** — only `OpenAIProvider`
   exists on disk; registration commented out
   (`provider/mod.rs:264-269`); `/api/v1/proxy*` not in `routes.rs`.
3. **Provider retry** — `ProviderError::is_retryable()` returns true for
   `RateLimited`/`Unavailable` but no caller retries; one `.send()`
   then return.
4. **`Retry-After` HTTP header on `/api/v1/proxy*` 502** — bare status,
   no header, no JSON envelope (`proxy.rs:109-112`).
5. **OpenAI `429` `RateLimited(60)` retry hint** — hardcoded 60 s is
   **dropped on the floor**, never emitted as `Retry-After`.
6. **No per-call Redis timeout** on `Script::invoke_async` /
   `cmd().query_async` — only 5 s *connection* timeout at
   `ConnectionManager::new`; no `with_timeout(...)` wrapper.
7. **No automatic Redis retry** in gate/track handlers.
8. **No jitter in any retry loop** — Slack alerts (1 s → 30 s), pricing
   cron, audit outbox, governance outbox. Pure exponential only.
9. **No server-side tool-execution timeout on `/execute`** — SDK runs
   the tool locally; the server has no watchdog.
10. **No client-initiated cancellation of in-flight `/gate` or
    `/execute`** — no DELETE/HEAD routes in `routes.rs:163-187`;
    `/cancel` is the only de-facto abort (separate call).
11. **No server-side deadline on `/execute` independent of `/gate`** —
    only `RedisCircuitBreaker` fail-fast at
    `execute.rs:199-201,225`.
12. **WS idle timeout** — 30 s ping is a probe, not an
    idle-disconnect policy; a silent client stays connected.
13. **WS per-org connection cap** — `MAX_SSE_PER_ORG=5` exists; WS has
    no equivalent cap.
14. **WS max frame size / max message size** — no
    `max_frame_size`/`max_message_size` override; axum defaults apply.
15. **`WS_PING_INTERVAL` / `WS_RECONNECT_MAX` env var** — grep returned
    zero matches.
16. **SQL-level `audit_outbox` queue depth cap** — only per-row retry
    cap (5) then DLQ; no global cap.
17. **Explicit semaphore / concurrency cap on `outbox/audit_drain`** —
    only `MAX_CONSECUTIVE_ERRORS=5` per tick break.
18. **`MAX_KEYS_SCAN` constant in Lua** — only `MAX_SCAN_ITERATIONS`
    (256) exists; `consume_v3.lua` has no scan / time-bound.
19. **Approval-rule predicate JSON byte cap** — `Option<serde_json::Value>`
    only, no byte validator.
20. **Stripe webhook** — no `stripe*.rs` files; Polar is the sole
    payment provider.
21. **`X-RateLimit-Limit` / `X-RateLimit-Remaining` / `X-RateLimit-Reset`
    on gate path** — grep returned zero matches in
    `proxy/http/gate/`; emitted only by `ip_rate_limit` middleware
    (per-IP edge).
22. **`Retry-After` HTTP header on gate** — gate uses body
    `retry_after_ms` / `retry_after_seconds` only.
23. **`MISSING_TOKEN` / `INVALID_KEY` / `EXPIRED_KEY` `GateErrorCode`
    variants** — registry has only `API_KEY_REVOKED` for auth-class;
    missing/invalid/expired flow through legacy `ApiError` envelope.
24. **`/track` `IDEMPOTENCY_IN_FLIGHT`** is emitted inline in
    `handlers.rs:5472` but NOT in `GateErrorCode::all()` — typed enum
    has 61 variants (`error_codes.rs:all()` asserts `len() == 61`),
    drift from inline emission.

### Not measured (would require load test)

1. Real Redis p99 RTT at production scale for `reserve_v3.lua`
   worst-case 256 SCAN + 256 MGET.
2. Worst-case first-request latency on Redis partition before the
   breaker trips (5 consecutive × 10 s acquire ≈ 50 s before
   short-circuit).
3. OpenAI upstream hung-socket behavior in practice — outer
   `TimeoutLayer` (30 s) is the only bound; no per-call
   `connect_timeout`.
4. WS reconnect storms — no server-side cap; SDK could reconnect
   indefinitely under split-brain.
5. Geo-block DB load latency at p99 — `mmdb` lookup is in-request hot
   path; only the 503 fail-CLOSED branch is verified.
6. PG pool contention under `/track` bursts — bounded ingestion queue
   has `QUEUE_CAPACITY=10_000`, `HARD=9_000` (drop oldest above),
   `MAX=15_000` (drop at cap), but actual Postgres write throughput is
   not measured.

### Drift between code and documentation

1. **`contracts/openapi.yaml` `GateResponse`** (lines 938-1033) is
   missing 8 wire fields present in the Rust struct
   (`internal.rs:551-734`): `approval_id`, `approval_timeout_seconds`,
   `approval_expires_at`, `execution_id`, `retry_after_ms`,
   `idempotent_replay`, `operation_id`, `decision_context`, `details`.
   `contracts/openapi.yaml:1-16` declares YAML canonical; Rust is
   wire-true.
2. **`/check` deprecation** — returns 410 GONE
   (`check.rs:46-74`) but YAML may still document it as active.

## How to verify

Any of these numbers can drift between this page and the actual code.
When that happens, **the code wins**. To re-derive:

```bash
# From NULLRUN repo root
git grep -nE 'TimeoutLayer|TimeoutDuration' backend/src/proxy/server.rs
git grep -nE 'failure_threshold|recovery_timeout_ms' backend/src/redis/breaker/config.rs
git grep -nE 'TTL|TIMEOUT|DURATION|interval' backend/src/retention.rs
git grep -nE 'MAX_' backend/src/redis/mod.rs
git grep -nE 'CAP|PATTERN|MAX_' validation_constants.toml
```

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
- [Compliance](../compliance/index.md) — geo / sanctions posture
