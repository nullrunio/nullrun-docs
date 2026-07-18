# API keys

An **API key** is how your code authenticates with the NullRun
gateway. The key identifies a single workflow, gives the agent the
permissions it needs, and (optionally) expires on a date you choose.

## Where you see it in the dashboard

API keys live under **Access → API keys** in the left sidebar. The
counter at the top of the page (`13 / 350`) tells you how many keys
your org has versus your plan's cap. The page shows every key with
its name, workflow, last-used timestamp, and expiration date.

## The mental model

Each workflow needs at least one API key to run. The key is what
the SDK uses to identify itself when it talks to the gateway. The
gateway uses the key to look up:

- Which workflow is calling (so it can apply the right policies)
- Which permissions the key has (gate / track / verify)
- Whether the key is still valid (not revoked, not expired)

You mint keys through the dashboard, paste them into your
application's environment, and the SDK takes care of the rest.

## How to create a key

1. **Access → API keys → New API key**.
2. Pick a workflow to bind the key to. The dropdown lists every
   workflow in your org.
3. Pick the permissions the key needs. The defaults
   (`gate`, `track`, `verify`) work for most agents.
4. Optionally set an expiration date. Keys without an expiration
   are valid until revoked.
5. Optionally mark as a **test key** if you're developing locally.
   Test keys bypass the budget cap — useful for trying things
   without setting up billing. Never use a test key in production.
6. Click **Create**.

The dashboard shows the new key value **once** — a string starting
with `nr_live_...`. Copy it into your secret manager
**immediately**. The dashboard will never show it again.

## What's in the response

When you create a key, the dashboard shows:

- **Key** — the public value (`nr_live_xxx...`). Use this in your SDK.
- **Secret key** — a second string for HMAC signing. Treat it like
  a password; never commit it to source control.
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
export NULLRUN_SECRET_KEY=sk_xxx...
```

The `api_key` is the public value the SDK sends on every request.
The `secret_key` is used for HMAC request signing — the gateway
verifies every request came from a holder of the secret.

You can pass the API key directly to `init()`:

```python
import nullrun
from nullrun import init

init(api_key="nr_live_xxx...")
```

Or set it via environment variable before the SDK starts:

```bash title="env"
export NULLRUN_API_KEY=nr_live_xxx...
python my_agent.py
```

For the secret key, the SDK reads `NULLRUN_SECRET_KEY` from the
environment. You can't pass it to `init()` — it has to be an env
var or read from your secret manager.

## Scopes

Each key has a list of permissions — what it can do:

| Scope | What it allows |
|---|---|
| `gate` | Call `/gate` (the policy decision endpoint). Required for any `@protect`-wrapped call. |
| `track` | Call `/track` (the spend tracking endpoint). Required for any LLM call. |
| `verify` | Call `/auth/verify` (the auth handshake). Almost always needed. |
| `*` | All of the above. The default if you don't specify. |

For most agents, the defaults work. A telemetry-only ingestor needs
just `track`. A read-only CI checker needs just `verify`.

## How to rotate a key

Rotating means replacing the secret on an existing key without
changing the public key value. Useful when the secret leaks but
the key itself is still safe.

1. **Access → API keys → find the key → Rotate**.
2. The dashboard generates a new secret and shows it once.
3. Update `NULLRUN_SECRET_KEY` in your environment / secret
manager / deployment config.
4. Restart the agent so it picks up the new secret.

The old secret stops working immediately. Any in-flight requests
with the old secret get a 401 — the agent's next call retries with
the new secret and succeeds.

## How to revoke a key

Revoking means deleting the key. Useful when:

- The key was leaked publicly
- The agent is decommissioned
- The workflow is being deleted

1. **Access → API keys → find the key → Revoke**.
2. Confirm.

The key stops working **immediately** — no grace period. If you
need zero-downtime rotation, rotate first (which gives the agent
time to pick up the new secret) and then revoke the old one.

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
- **One test key** — for local development. Bypasses the budget
  cap. Never deploys to production.

### "Can I share a key between two workflows?"

No. Each key is bound to exactly one workflow at creation time.
If you need the same agent logic against two workflows (for
example, A/B testing), create two keys and switch between them
based on your A/B routing.

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
