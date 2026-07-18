# Sensitive tools

A **sensitive tool** is one that should never run without a human
paying attention. Sending an email, moving money, deleting a record —
all of these have consequences the agent can't easily undo.

The SDK ships with a built-in list of sensitive tool patterns that
**always block or pause**, regardless of your policies. This page
explains what's on the list, why, and how to extend it.

## What's on the list

The SDK matches these patterns case-insensitively, by default:

| Category | Tool patterns |
|---|---|
| **Money** | `stripe.charge`, `stripe.refund`, `stripe.payout`, `payment.process`, `send_payment`, `create_invoice` |
| **Email & messaging** | `send_email`, `send_sms`, `send_slack`, `send_discord`, `slack_send_message`, `office365_send_email` |
| **Database destructive** | `db.write`, `db.delete`, `db.drop`, `db.truncate`, `execute_sql`, `write_query`, `create_table` |
| **External API writes** | `api.post`, `api.put`, `api.delete`, `requests_delete` |
| **Files & storage** | `file.write`, `file.delete`, `s3.delete`, `delete_file` |
| **Admin** | `admin.delete`, `admin.create_user`, `admin.disable_user` |
| **Code execution** | `python_repl`, `execute_code`, `bash`, `shell`, `terminal` |

These match the **patterns** you can use in your own
[ToolBlock policies](tool-policies.md), but they apply **independently**
of any policy you create.

## Why the list exists

If the gateway is unreachable, the gate has to choose: block the
call, or let it through. Most of the time "let it through" is fine —
the agent retries when the network comes back, no harm done.

For sensitive operations, that's the wrong default. Letting through
a `stripe.charge` when the policy check failed means the agent could
move money without anyone knowing. The blast radius is "agent
deleted production data" or "agent leaked your data to an attacker" —
worse than a noisy stop.

So the SDK fails **closed** for sensitive tools: when the gateway
is unreachable and the policy decision can't be made, the call is
denied. You see `NullRunBlockedException` in the agent log instead of
the operation going through.

## What's NOT on the list

The SDK doesn't try to predict every dangerous tool. Some patterns
are domain-specific:

- **Code execution in your sandbox** — if your agent runs code in
  a sandbox where blast radius is contained, the list is too strict.
- **Internal write APIs** — `inventory.update_stock` is a write but
  it's reversible; the list doesn't know.
- **Read operations** — never sensitive regardless of the tool.

You can extend the list to be more or less strict for your use case.

## How to extend the list

If you want additional patterns to fail closed (block when the
gateway is unreachable), register them after `init()`:

```python title="extend_sensitive.py"
import nullrun
from nullrun import init
from nullrun.decorators import get_protected_runtime

init(api_key="nr_live_...")

runtime = get_protected_runtime()
runtime.register_sensitive_tools([
    # Anything starting with "refund_" fails closed
    "refund_*",
    # Internal write tools
    "inventory.update_stock",
    "crm.*",
])
```

The patterns use the same glob matcher as
[Tool policies](tool-policies.md#how-to-write-the-patterns). The
extensions apply to **your** process — they don't propagate to other
processes or to the gateway.

If you want to **remove** something from the built-in list (because
your sandbox makes it safe), pass `False` as the second argument:

```python title="unregister_sensitive.py"
runtime.register_sensitive_tools(["stripe.charge"], override=False)
# or remove a single entry
runtime.remove_sensitive_tool("stripe.charge")
```

Be careful removing built-ins. The list exists because of historical
incidents — every entry has a "don't ship without it" story.

## What shows up in the dashboard

When the SDK blocks a sensitive tool, the call appears in **Decision
History** as:

- **Decision**: `block`
- **Reason**: `sensitive_tool` (vs `policy_block` for your own policies)
- **Source**: `sdk` (the block happened in the SDK, not on the gateway)

This tells you the SDK stopped the call locally, not because a policy
said so but because the tool is on the sensitive list and the policy
check couldn't complete.

For sensitive tools you want to allow after explicit human review,
pair them with the [Human approval](human-approval.md) flow instead
of removing them from the sensitive list. The approval row in the
dashboard gives you an audit trail.

## See also

- [Tool policies](tool-policies.md) — your own blocking rules
- [Tool catalog](../reference/llm-tool-catalog.md) — common tool
  names with risk ratings and a recommended starter list
- [Human approval](human-approval.md) — the safer alternative to
  removing a tool from the sensitive list
- [Circuit breaker](circuit-breaker.md) — when the gateway is
  unreachable, sensitive tools fail closed; everything else may
  fall through
