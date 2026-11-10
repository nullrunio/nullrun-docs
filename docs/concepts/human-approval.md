---
title: Human approval
maturity: beta
description: The approval rule object, its typed predicates, and the SHA-256 action_digest that binds a grant to the exact payload the operator approved.
---

# Human approval

Some operations need a human to click **Approve** before they run.
Sending an email to a customer, moving money, deleting a record —
operations where you want a paper trail and a conscious decision.

When the agent hits an approval rule, the call parks. The agent stays
parked until a human decides, or the approval expires.

This page covers the rule and the wire contract. The operator's review
surface — what a pending request shows, how to approve or deny it — is
in [Approvals](approvals.md).

## Approval rules — separate from ToolBlock

Approval rules are not `ToolBlock` policies with an `action =
require_approval` field. They are a separate rule object:

| Field | Purpose |
|---|---|
| `workflow_id` | The workflow the rule applies to. Every rule is scoped to one workflow. |
| `tool_patterns` | Glob patterns matching the tool name |
| `per_call_threshold_cents` | Projected-cost threshold. A wire field; the control center sends `null`. |
| `action_predicate` | Typed predicate over the call's impact |
| `action_label` | Label shown in the control center. Up to 200 bytes of text. The characters are limited to letters, digits, spaces and ` _.,-&()$%!?+=*`. |
| `priority` | Order among the rules that match. Lower wins. Range 0–1000. |
| `expires_in_seconds` | How long the operator has to decide. 30–3600 seconds. |
| `risk_level` | `LOW`, `MEDIUM` or `HIGH`. Defaults to `MEDIUM`. |

Rules live under **Governance → Approval rules**. That page needs the
approvals feature, which is on Growth and above.

When a protected call matches an approval rule, the gate returns
`decision = "require_approval"` and the SDK parks until the operator
decides.

## When a rule fires

Two fields can fire the same rule:

- **`per_call_threshold_cents`** — projected execution cost in cents,
  evaluated against the estimated tokens the SDK reports.
- **`action_predicate`** — a typed condition over a structured impact
  extracted from the live call.

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

`direction` is `outflow` or `inflow`. `operator` is `gt`, `gte` or
`eq`. `threshold_minor` is a non-negative integer count of cents, so
`5000` is `$50.00`. `currency` must be `USD`.

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

The `tool_parameters` predicate reads the canonical argument bag on the
wire: `tool_arguments`, then `tool_params`. MCP tool calls carry it.
A plain `@protect` function does not, so the predicate cannot be
evaluated and the call escalates to a human instead of matching on the
argument. The `money_amount` predicate is unaffected — it reads
`business_impact`, which the SDK does ship.

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
| The executing tool is outside the approved tool set | Refused, `error_code = "NR-A017"` |

## Approval resume flow

1. The SDK sends the gate request with the live impact payload. The
   gate evaluates the approval rules and one matches.
2. The gate creates a pending approval row with the payload, its
   digest, and an expiry set server-side. It notifies the configured
   channels.
3. The gate returns `decision = "require_approval"` with the
   approval id and the timeout.
4. The SDK parks until the operator decides.
5. The operator clicks Approve or Deny in the control center.
6. The gateway publishes the resolution on the WebSocket channel.
7. The SDK wakes up and resumes with the operator's outcome.

A denial reaches the agent as `NullRunApprovalDeniedError` (`NR-A011`).

If no decision arrives within the timeout, the SDK **fails closed**
and raises `NullRunApprovalExpiredError` (`NR-A012`). There is no
HTTP polling fallback for approvals: a silent network must not
silently approve a privileged action.

An approval request reaches your channels only if the
`approval_required` event subscription is on. The **Approval required**
subscription is off in the notification settings by default. An
organization that has never saved its notification settings still
announces approval requests on its configured channels.
See [Notifications](notifications.md).

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

- [Approvals](approvals.md) — the operator's review surface
- [Tool policies](tool-policies.md) — `ToolBlock` rules
- [Sensitive tools](sensitive-tools.md) — when blocking is enough
- [Workflows → How to control one](workflow.md#how-to-control-one) —
  Pause and Kill work the same way
- [API keys](api-keys.md) — how to mint a key bound to a workflow

<figure class="nr-shot">
  <img class="nr-shot__light" src="../../assets/images/screenshots/approval-rules-light.png"
       alt="Approval rules page with the New rule button highlighted in the top right."
       loading="lazy" decoding="async">
  <img class="nr-shot__dark" src="../../assets/images/screenshots/approval-rules-dark.png"
       alt="Approval rules page with the New rule button highlighted in the top right."
       loading="lazy" decoding="async">
  <figcaption class="nr-shot__caption">Governance · Approval rules · New rule</figcaption>
</figure>
