---
title: API keys
maturity: stable
description: Create a key, bind it to a workflow, rotate it, and revoke it — and what the HMAC secret is for.
---

# API keys

An **API key** is how your code authenticates with the NullRun
gateway. The key identifies one workflow, carries the scopes the key
may use, and optionally expires on a date you choose.

## Where you see it

API keys live under **Access → API keys** in the sidebar. The counter
at the top of the page shows how many keys your organization has
against your plan's cap.

| Plan | Keys |
|---|---|
| Lite | 10 |
| Starter | 15 |
| Growth | 100 |
| Scale | 350 |
| Enterprise | Unlimited |

The cap is enforced by the server. Creating a key past the cap is
refused with `plan_limit_exceeded`.

## How to create a key

1. **Access → API keys → New API key**.
2. Give the key a **name**. It shows up in the list and in the audit
   log, so make it descriptive.
3. Pick the **workflow** the key belongs to. A key belongs to exactly
   one workflow, and the gateway uses that binding to apply the right
   policies. The server refuses a key with no workflow.
4. Pick an **expiration**: **Never**, **24 hours**, **7 days**,
   **30 days**, or **90 days**. A key with no expiration works until
   you revoke it.
5. Click **Create**.

The dashboard shows the key value **once**. Copy it into your secret
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

## What you get back

| Field | What it is |
|---|---|
| **Key** | The public value, starting with `nr_live_`. The SDK sends it on every request. |
| **HMAC secret** | A second secret that signs requests. The SDK reads it from `NULLRUN_SECRET_KEY`. |
| **Prefix** | A short non-secret fragment of the key. It identifies the key in list views and logs. |
| **Workflow** | The workflow the key is bound to. |
| **Scopes** | The permissions the key carries. |

Both secrets are shown exactly once. After you close the dialog they
are gone. If you lose them, rotate the key.

## Using the key in the SDK

The SDK reads two environment variables:

```bash title="env"
export NULLRUN_API_KEY=nr_live_xxx...
export NULLRUN_SECRET_KEY=...
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
came from the holder of that secret: the SDK signs the request and the
gateway verifies the signature. Set the secret whenever the key has
one.

The runtime is created lazily on the first `@protect` call. Set the
environment variables, then start your agent.

## Scopes

A scope says what a key may do. Every new key gets the full set.

| Scope | What it allows |
|---|---|
| `gate` | Ask the gateway for a policy decision on a protected call |
| `execute` | Re-check a call after an approval was granted |
| `track` | Report the token counts and cost of a completed call |
| `verify` | Complete the authentication handshake on first use |
| `*` | All of the above |

Most agents need all four. A telemetry-only ingestor needs `track`.
A read-only checker needs `verify`.

## Rotating a key

Rotation issues a **new key value**. The new key keeps the old key's
name, scopes, workflow binding and HMAC secret, so it does the same
job — only the value changes.

The old key keeps working for a grace window. Deploy the new value
first, confirm the agent still runs, then revoke the old key. Nothing
breaks in between.

```bash title="shell"
curl -X POST "https://api.nullrun.io/api/v1/orgs/$ORG_ID/api-keys/$KEY_ID/rotate" \
  -H "Authorization: Bearer $NULLRUN_ADMIN_TOKEN"
```

The response carries the new key value. It is shown once.

## Revoking a key

Revoking stops the key. The next request with that key is refused
with `401 API_KEY_REVOKED`. There is no grace period.

Revoke a key when:

- the key leaked
- the agent behind it is decommissioned
- the workflow it belongs to is going away

```bash title="shell"
curl -X DELETE "https://api.nullrun.io/api/v1/orgs/$ORG_ID/api-keys/$KEY_ID" \
  -H "Authorization: Bearer $NULLRUN_ADMIN_TOKEN"
```

Revoking is an audit event. The audit log records who revoked the key
and when.

## Listing and searching

The **API keys** page lists every key in your organization. You can
search by name, filter by workflow and filter by status.

Each row shows:

- **Name**
- **Workflow**
- **Prefix**
- **Last used** — when the key last made a request
- **Expires** — the expiry date, or "Never"
- **Status** — active or revoked

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

The **Last used** column gives you the most recent activity. The
audit log gives you every call, keyed by the key's prefix rather than
its full value.

### "Should I ever disable the gate?"

No. Without a protected call there is no decision, so nothing is
enforced and nothing is recorded.

## See also

- [Workflows](workflow.md) — what the key is bound to
- [Configuration](../getting-started/configuration.md) — the
  environment variables
- [Troubleshooting](../troubleshooting.md) — "why am I getting 401?"
