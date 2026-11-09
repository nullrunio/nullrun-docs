---
title: Human approval
maturity: beta
description: Bind approvals to a typed BusinessImpact predicate and a SHA-256 action_digest, so a grant is refused when the action payload changes.
---

# Human approval

Some operations need a human to click **Approve** before they run.
Sending an email to a customer, moving money, deleting a record —
operations where you want a paper trail and a conscious decision.

In the dashboard, pending approvals live under **Approvals** in the
sidebar. When the agent hits an approval rule, the call parks. The
agent stays parked until a human clicks **Approve** or **Deny**, or
the approval times out.

## Approval rules — separate from ToolBlock

Approval rules are not `ToolBlock` policies with an `action =
require_approval` field. They are a separate rule object:

| Field | Purpose |
|---|---|
| `name` | Display name for the rule |
| `tool_patterns` | Glob patterns matching the tool name |
| `per_call_threshold_cents` | Projected-cost threshold |
| `action_predicate` | Typed `BusinessImpact` predicate |
| `priority` | Ordering for tied rules |
| `expires_in_seconds` | How long the operator has to decide |
| `action_label` | Display label shown in the dashboard |
| `risk_level` | `LOW`, `MEDIUM` or `HIGH` |

When a protected call matches an approval rule, the gate returns
`decision = "require_approval"` and the SDK parks until the operator
decides.

## Predicate kinds

Two predicate fields can fire the same approval rule:

- **`per_call_threshold_cents`** — projected execution cost in cents,
  evaluated against the estimated tokens the SDK reports.
- **`action_predicate`** — a typed condition over a structured
  `BusinessImpact` extracted from the live call.

When both are set, the rule fires only when **both** pass. Either may
be absent, in which case it does not contribute. A rule with neither
matches every call.

### Typed predicates

Two predicate kinds are supported on `action_predicate`.

**`money_amount`** — a per-call monetary threshold:

```json
{
  "kind": "money_amount",
  "direction": "outflow",
  "operator": "gt",
  "threshold_minor": 5000,
  "currency": "USD"
}
```

**`tool_parameters`** — a disjunction over up to 5 named parameters,
with `equals`, `one_of`, `numeric_range`, `regex` and `exists`
matchers:

```json
{
  "kind": "tool_parameters",
  "trigger_logic": {"logic": "any"},
  "conditions": [
    {"param_name": "refund_amount", "matcher": {"type": "numeric_range", "min": 500}},
    {"param_name": "recipient", "matcher": {"type": "regex", "pattern": "^(?!internal@).*"}}
  ]
}
```

`trigger_logic` takes `{"logic": "any"}`, `{"logic": "all"}` or
`{"logic": "groups", "groups": [[0, 1], [2]]}`. The groups form lists
AND-groups of condition indices joined by OR. The default is `any`.

The `tool_parameters` predicate reads values out of the arguments the
SDK ships with every `@protect`-decorated function. The rule
references a value by `param_name`, and the gate evaluates it
directly. No extra decorator is needed to make a tool eligible for
`tool_parameters` rules.

## `action_digest` — the binding

The gate computes a SHA-256 digest of the action's impact payload
and stores it on the approval row.

After the operator clicks Approve, the SDK sends the live payload and
its digest back to the gateway on the post-approval call. The gateway
recomputes the digest from that payload and compares it with the one
the operator approved. The comparison is atomic, so two concurrent
re-checks cannot both spend the same grant.

**The digest binds the approval to the exact payload.** A changed
amount, a changed argument, or a changed tool name makes the digest
differ from the approved one, and the call is refused:

| Situation | Result |
|---|---|
| The payload matches the approved one | The grant is consumed and the call proceeds |
| The impact payload drifted | Refused, `error_code = "NR-A013"` |
| The tool digest drifted | Refused, `error_code = "NR-A014"` |
| The grant was already consumed | Refused, `error_code = "NR-A015"` |

## Approval resume flow

1. The SDK sends the gate request with the live impact payload. The
   gate evaluates the approval rules and one matches.
2. The gate creates a pending approval row with the payload, its
   digest, and an expiry set server-side. It notifies the configured
   channels.
3. The gate returns `decision = "require_approval"` with the
   approval id and the timeout.
4. The SDK parks until the operator decides.
5. The operator clicks Approve or Deny in the dashboard.
6. The gateway publishes the resolution on the WebSocket channel.
7. The SDK wakes up and resumes with the operator's outcome.

If no decision arrives within the timeout, the SDK **fails closed**
and raises `NullRunApprovalExpiredError` (`NR-A012`). There is no
HTTP polling fallback for approvals: a silent network must not
silently approve a privileged action.

## What you see in the dashboard

The **Approvals** page lists every pending, approved, denied and
expired request. Each row shows:

- The tool the agent wanted to call
- The workflow that requested it
- The action digest — the first 16 hex characters, the full digest in
  the tooltip
- For typed predicates, the rendered impact summary
- How long ago it was created
- How long until it expires

<figure class="nr-shot">
  <img class="nr-shot__light" src="../../assets/images/screenshots/approvals-light.png"
       alt="Approvals page listing every pending, approved, denied and expired request."
       loading="lazy" decoding="async">
  <img class="nr-shot__dark" src="../../assets/images/screenshots/approvals-dark.png"
       alt="Approvals page listing every pending, approved, denied and expired request."
       loading="lazy" decoding="async">
  <figcaption class="nr-shot__caption">Approvals</figcaption>
</figure>

Click an approval to see the full context: what the agent was trying
to do, the tool's arguments, and any notes you attached.

## How to approve or deny

Open a request in the **Approvals** page. You see the agent's goal,
the tool, the typed impact summary or the projected cost, the action
digest, and how long the request has been pending.

Two buttons:

- **Approve** — the grant is released and the agent resumes. The
  gateway re-checks the digest against the live payload on the way
  out and refuses on a mismatch.
- **Deny** — the gateway rejects and the agent raises
  `NullRunApprovalDeniedError` (`NR-A011`).

If neither button is clicked within the request's window, it expires
and the SDK raises `NullRunApprovalExpiredError` (`NR-A012`).

## Notification channels

When an approval is created, the gateway notifies every active channel
configured on your organization:

- **Slack** — through your organization's installed Slack app.
- **Webhook** — a generic HTTPS POST with an HMAC-SHA256 signature.

Disable a channel under **Notifications** in the sidebar (Channels,
Alert rules, and an Event subscriptions matrix).

<figure class="nr-shot">
  <img class="nr-shot__light" src="../../assets/images/screenshots/approval-rules-light.png"
       alt="Approval rules page with the New rule button highlighted in the top right."
       loading="lazy" decoding="async">
  <img class="nr-shot__dark" src="../../assets/images/screenshots/approval-rules-dark.png"
       alt="Approval rules page with the New rule button highlighted in the top right."
       loading="lazy" decoding="async">
  <figcaption class="nr-shot__caption">Governance · Approval rules · New rule</figcaption>
</figure>

## Programmatic approval

The dashboard is for humans. A CI bot or an on-call rotation can
decide through the same endpoints:

```bash title="approve_via_api.sh"
curl -X POST "https://api.nullrun.io/api/v1/orgs/$ORG_ID/approvals/$APPROVAL_ID/approve" \
  -H "Authorization: Bearer $NULLRUN_API_KEY"

# Or deny explicitly
curl -X POST "https://api.nullrun.io/api/v1/orgs/$ORG_ID/approvals/$APPROVAL_ID/deny" \
  -H "Authorization: Bearer $NULLRUN_API_KEY"
```

Deciding twice is not an error. Approving an already-decided request
returns `409 APPROVAL_ALREADY_DECIDED`.

## When to use approval instead of blocking

Approval fits when:

- The operation is sensitive but you want the agent to be able to do
  it under human review.
- The blast radius is bounded — one email against a whole database
  drop.
- Someone is on call and can review within minutes.

Blocking fits when:

- The operation is never legitimate, such as `db.drop` in a
  read-only workflow.
- The blast radius is unbounded.
- No one can review approvals in time.

Approval is a feature, not a default. Start by blocking, and move
specific patterns to approval as the need arises.

## What's logged

Every approval decision lands in **Governance → Audit log**. Filter by
actor (the approver), decision (`approved` or `denied`) and time
window. The row carries the action digest and the tool name.

The action digest is the anchor that proves the operator approved the
exact payload the agent sent — not "any refund", but that amount and
those arguments.

## See also

- [Tool policies](tool-policies.md) — `ToolBlock` rules
- [Sensitive tools](sensitive-tools.md) — when blocking is enough
- [Workflows → How to control one](workflow.md#how-to-control-one) —
  Pause and Kill work the same way
- [API keys](api-keys.md) — how to mint a key bound to a workflow
