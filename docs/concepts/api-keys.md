---
title: API keys
maturity: stable
description: Create an API key, bind it to one workflow, rotate it without downtime, revoke it, and understand the HMAC secret that signs every request.
---

# API keys

An **API key** authenticates your code with the NullRun gateway. It
identifies one workflow, and it comes with a second secret that signs
every request.

## Where you see it

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

## How to create a key

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
  <img class="nr-shot__light" src="../../assets/images/screenshots/api-keys-list-light.png"
       alt="API keys list with the New key button highlighted in the top right."
       loading="lazy" decoding="async">
  <img class="nr-shot__dark" src="../../assets/images/screenshots/api-keys-list-dark.png"
       alt="API keys list with the New key button highlighted in the top right."
       loading="lazy" decoding="async">
  <figcaption class="nr-shot__caption">API keys · New key</figcaption>
</figure>

<figure class="nr-shot">
  <img class="nr-shot__light" src="../../assets/images/screenshots/api-key-new-light.png"
       alt="New API key dialog open — Key name field, Workflow dropdown, Create button."
       loading="lazy" decoding="async">
  <img class="nr-shot__dark" src="../../assets/images/screenshots/api-key-new-dark.png"
       alt="New API key dialog open — Key name field, Workflow dropdown, Create button."
       loading="lazy" decoding="async">
  <figcaption class="nr-shot__caption">API keys · New key dialog</figcaption>
</figure>

## What a key is made of

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

## Using the key in the SDK

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
`NULLRUN_SECRET_KEY` is read at start-up and replaced by the server's
value whenever the server returns a key version. A key that has never
had a version returns none, so the SDK keeps the value you set.

`nullrun.init()` raises `NullRunAuthenticationError` when no key is
set. It creates the runtime and authenticates it against the gateway
immediately, so set the environment variables before you call it.

## Scopes

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

## Rotating a key

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

## Revoking a key

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

## Listing keys

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

## Common questions

### "How many keys do I need?"

One per workflow at minimum. For production, one key per environment
and one key per service. That way you can revoke staging without
touching production, and rotate one instance without restarting the
others.

### "Can one key serve two workflows?"

No. A key is bound to one workflow when it is created. If the same
agent logic runs against two workflows, create two keys and pick
between them.

### "What happens when a key expires?"

Requests with that key stop working. The error is `401
API_KEY_EXPIRED`. Rotate to get a new value, or create a new key.

### "Can I see who used a key?"

The **Last used** column gives you the most recent activity. The audit
log records gate decisions for your organization on plans that include
it (Growth and above). A row does not name the key that made the call.

### "Should I ever disable the gate?"

No. Without a protected call there is no decision, so nothing is
enforced and nothing is recorded.

## See also

- [Workflows](workflow.md) — what the key is bound to
- [Configuration](../getting-started/configuration.md) — the
  environment variables
- [Troubleshooting](../troubleshooting.md) — "why am I getting 401?"
