title: API keys
maturity: stable
description: Scopes, two-phase rotation, revocation, and the binding between an API key, its workflow, and its policy cache.
# API keys

An **API key** is how your code authenticates with the NullRun
gateway. The key identifies a single workflow, gives the agent the
permissions it needs, and (optionally) expires on a date you choose.

## Where you see it in the dashboard

API keys live under **Access → API keys** in the left sidebar. The
counter at the top of the page (`N / <plan-cap>`) tells you how many
keys your org has versus your plan's cap. The page shows every key
with its name, workflow, last-used timestamp, and expiration date.

Per-plan key cap: Lite = 10, Starter = 15, Growth = 100,
Scale = 350, Enterprise = unlimited (see
[Billing & Plan → Per-tier caps](billing.md#per-tier-caps)). The
cap is enforced server-side — the create handler rejects with
`plan_limit_exceeded` once you hit it.

## The mental model

Each workflow needs at least one API key to run. The key is what the
SDK uses to identify itself when it talks to the gateway. The gateway
uses the key to look up:

- Which workflow is calling (so it can apply the right policies)
- Which permissions the key has (`gate` / `execute` / `track` / `verify`)
- Whether the key is still valid (not revoked, not expired)

You mint keys through the dashboard, paste them into your
application's environment, and the SDK takes care of the rest.

## How to create a key

1. **Access → API keys → New API key**.
2. Pick a workflow to bind the key to. The dropdown lists every
   workflow in your org. (Each key is **workflow-scoped** — one key
   represents one agent run, not one workspace.)
3. Pick an **Expires** window: **Never** (default), **24 hours**,
   **7 days**, **30 days**, or **90 days**. Keys without an
   expiration are valid until revoked.
4. Click **Create**.

Scopes (`gate` / `execute` / `track` / `verify`) are auto-assigned
to every new key and are not user-customizable in the dialog — the
gateway needs all four to do its job.

The dashboard shows the new key value **once** — a string starting
with `nr_live_...`. Copy it into your secret manager **immediately**.
The dashboard will never show it again.

<figure class="nr-shot">
  <img class="nr-shot__light" src="../../assets/images/screenshots/api-keys-list-light.png"
       alt="API keys list with the New key button highlighted in the top right.">
  <img class="nr-shot__dark" src="../../assets/images/screenshots/api-keys-list-dark.png"
       alt="API keys list with the New key button highlighted in the top right.">
  <figcaption class="nr-shot__caption">API keys · New key</figcaption>
</figure>

<figure class="nr-shot">
  <img class="nr-shot__light" src="../../assets/images/screenshots/api-key-new-light.png"
       alt="New API key dialog open — Key name field, Workflow dropdown, Create button.">
  <img class="nr-shot__dark" src="../../assets/images/screenshots/api-key-new-dark.png"
       alt="New API key dialog open — Key name field, Workflow dropdown, Create button.">
  <figcaption class="nr-shot__caption">API keys · New key dialog</figcaption>
</figure>

## What's in the response

When you create a key, the dashboard shows:

- **Key** — the public value (`nr_live_xxx...`). Use this in your SDK.
- **HMAC secret key** — a second 32-byte hex string for request
  signing. Treat it like a password; never commit it to source
  control. The SDK stores it under `NULLRUN_SECRET_KEY`.
- **Key prefix** — the first 12 characters, used in list views.
- **Workflow** — the bound workflow (you picked this on creation).
- **Scopes** — the permissions you granted.

The dashboard shows the full key and secret **exactly once**. After
you close the modal, the values are gone forever. If you lose them,
you must rotate the key (see below).

## How the SDK uses the key

The SDK needs two values from you:

```bash title="env"
export NULLRUN_API_KEY=nr_live_xxx...
export NULLRUN_SECRET_KEY=...
```

The `api_key` is the public value the SDK sends on every request.
The `hmac_secret` is used for HMAC-SHA256 request signing — the
gateway verifies every request came from a holder of the secret.

In production deployments, HMAC is required. Without it, every SDK
request returns 401.

The runtime is created lazily on the first `@protect` call from
`NULLRUN_API_KEY`. Set `NULLRUN_API_KEY` (and `NULLRUN_SECRET_KEY`
for HMAC) in the environment before the first protected call runs:

```bash title="env"
export NULLRUN_API_KEY=nr_live_xxx...
python my_agent.py
```

The HMAC secret is read from `NULLRUN_SECRET_KEY` in the
environment. It is set once per process.

## Scopes

Each key has a list of permissions — what it can do. Only the four
values below are accepted; any other value is rejected at the API
key creation step.

| Scope | What it allows |
|---|---|
| `gate` | Call `/api/v1/gate` (the policy decision endpoint). Required for any `@protect`-wrapped call. |
| `execute` | Call `/api/v1/execute` (the post-approval re-check after a `require_approval` decision). |
| `track` | Call `/api/v1/track` (the spend tracking endpoint). Required for any LLM call. |
| `verify` | Call `/api/v1/auth/verify` (the auth handshake on first use). Almost always needed. |
| `*` | Wildcard — all of the above. The default if you don't specify. |

For most agents, the defaults work. A telemetry-only ingestor needs
just `track`. A read-only CI checker needs just `verify`.

## How to rotate a key

Rotating creates a new key and invalidates the old one. In-flight
calls finish normally.

## How to revoke a key

Revoking means deleting the key. Useful when:

- The key was leaked publicly
- The agent is decommissioned
- The workflow is being deleted

Use `POST /api/v1/orgs/{org_id}/api-keys/{key_id}/rotate` first to
generate a replacement, then `DELETE` the old one.

The key stops working immediately — no grace period.

## Listing and searching

The **API keys** page lists every key in your org. You can search
by name (substring match), filter by workflow, or filter by status
(active / revoked).

Each row shows:

- **Name** — what you set when creating
- **Workflow** — the bound workflow
- **Prefix** — first 12 characters of the key (`nr_live_abc...`)
- **Last used** — when the SDK last made a request with this key
- **Expires** — when the key stops working (or "Never")
- **Status** — active / revoked

Click a row to see full details. The full key value is never shown
again — only the prefix.

## Common questions

### "How many keys do I need?"

One per workflow, minimum. For production:

- **One key per environment** — separate keys for production,
  staging, dev. Makes it easy to revoke staging without affecting
  production.
- **One key per service** — if your agent runs in three
  containers, give each its own key. Makes it easy to rotate one
  without restarting the others.

Do not disable the gate in production — you'll lose enforcement.

### "Can I share a key between two workflows?"

No. Each key is bound to exactly one workflow at creation time.
If you need the same agent logic against two workflows (for example,
A/B testing), create two keys and switch between them based on your
A/B routing.

### "What happens when my key expires?"

The key stops working at the expiration timestamp. Calls return
`401 api_key_expired`. Rotate the key (which generates a new secret
but keeps the same key value) or create a new key entirely.

### "Can I see who used a key?"

The **Last used** column shows the most recent activity. The audit
log shows every individual call. The audit log records the
key prefix, not the full key — so you can correlate usage without
exposing the secret.

## See also

- [Workflows](workflow.md) — what the key is bound to
- [Troubleshooting](../troubleshooting.md) — "why am I getting 401?"
- [Configuration](../getting-started/configuration.md) — env vars
  for keys

## Deep dive

### Mechanism

An API key is two independent secrets minted at create time
(`backend/src/proxy/http/api_keys.rs::create_api_key_handler`):
a raw key of shape `nr_live_<32 alphanumerics>` from
`auth/mod.rs::generate_api_key()` (62⁵² search space from
`OsRng`), and an HMAC secret of shape `<64 hex chars>` (32 random
bytes) from `auth/mod.rs::generate_hmac_secret()`. The HMAC
secret is independent from the raw key — a 2026-07-06 bug-fix
split them after a prior version reused `generate_api_key()` for
both, giving HMAC a 0-bit security margin. Each request signs
with `HMAC-SHA256(secret, timestamp:api_key:body_hash)` and the
gateway verifies with constant-time compare via
`auth/hmac.rs::verify_hmac_signature`. Lookup is two-step:
`ApiKey::compute_fingerprint` returns `SHA-256(raw_key)[:16]` hex
for O(1) DB pre-check before Argon2 verify.

Multi-version rotation works through `HmacKeyStore`
(`auth/hmac.rs`): `load_key_versions_with_plaintext` keeps a
`HashMap<api_key_id, Vec<KeyVersion>>` in `Arc<RwLock>`, and
mutations publish `HmacKeyEvent` over Redis pub/sub channel
`nullrun:hmac:keys` so other pods re-apply via
`HmacKeySubscriber::spawn`. Plaintext never crosses pub/sub —
receivers re-fetch locally.

Revocation is two-phase (ADR-010). When
`NULLRUN_AUTH_DRAIN_ENABLED=1`, the handler runs
`transition_to_rotating → drain_in_flight → transition_to_revoked`
via `proxy/auth_lifecycle/`. In-flight count lives at
`in_flight:{org_id}:{api_key_id}` and is bumped via
`redis/scripts/in_flight_inc_v1.lua` — Lua (not `INCR`) because
`INCR` drops TTL, which would leave a stuck counter after a pod
restart. Default TTL 300s aligns with `AUTH_CACHE_TTL_SECS`.

### Guarantees

- HMAC timestamp freshness is a 5-minute sliding window
  (`max_age_seconds = 300`) — replay protection via age check,
  not nonce storage.
- Revoke is drain-aware: in-flight requests finish before the key
  is terminal, so a long-running `/check` cannot lose its
  reservation mid-flight.
- Redis hiccup during in-flight increment is fail-CLOSED — the
  request is rejected because the supervisor cannot guarantee
  accurate counts during a future revoke
  (`backend/src/redis/in_flight.rs::inc_in_flight`).
- Server-minted `api_key_id` (UUIDv7), bound to `(org_id,
  api_key_id)` in `organization_api_keys` — client-supplied IDs
  are rejected.
- HMAC secret returned to the dashboard ONCE at create time —
  stored as a hash on the server; never re-served.

### Patterns

- Per-workflow binding (Phase 139): `workflow_id` column on
  `organization_api_keys`, one key = one workflow, used as the
  per-key group axis on `/control-center/api-keys`.
- Five scopes auto-assigned at create: `gate`, `execute`, `track`,
  `verify`, `*`. A telemetry-only ingestor ships `track` only;
  a CI checker ships `verify` only.
- `last_used_at` is updated via the auth-cache hit path on every
  `/check` / `/execute` / `/track` request that bears a valid
  `X-API-Key`.
- Per-plan key cap (`seats_limit`-style lookup in
  `dashboard::parse_plan_limits`): Lite = 10, Starter = 15,
  Growth = 100, Scale = 350, Enterprise = unlimited. ADR-057
  Lite Trial overlays Scale's cap for the trial window via
  `resolve_plan_for_org_overlay_strict`.

### Approaches

- Considered client-supplied `key_id`. Rejected — ownership
  ambiguity on multi-tenant boundaries and a replay surface
  against `consume_approved`.
- Considered a single-version HMAC secret store. Chosen
  multi-version so an in-flight SDK can keep signing with the old
  secret while the dashboard has already cut over to the new one
  (rotation without downtime).
- Considered `INCR` + separate `EXPIRE` for in-flight count.
  Rejected — the gap between `INCR` and `EXPIRE` lets a counter
  land without a TTL and never recover. Lua serializes
  read-modify-write under Redis's executor so `SET … EX ttl` is
  atomic.

### Limitations

- Raw key value is shown exactly once. Losing it forces rotation
  (revoke + create).
- HMAC secret is also shown exactly once; losing it forces
  regeneration even if the raw key is preserved.
- Cross-pod split-brain: a pub/sub outage leaves remote pods with
  a stale `HmacKeyStore` until the next event. Trade-off documented
  in `auth/hmac.rs` ("stale peers until the next event" over
  "blocking the SDK request behind a Redis call").
- Two-phase revoke is dormant behind
  `NULLRUN_AUTH_DRAIN_ENABLED=1`; without the flag the handler
  falls through to immediate revoke (preserves the pre-Phase-C
  wire contract).
