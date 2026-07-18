# Human approval

Some operations need a human to click **Approve** before they run.
Sending an email to a customer, moving money, deleting a record —
operations where you want a paper trail and a conscious decision.

In the dashboard, pending approvals live under **Approvals** in the
sidebar. When the agent hits a tool that requires approval, the call
pauses. The agent stays paused until a human clicks **Approve** or
**Deny**, or the approval expires.

## When does the agent need approval?

Approval is triggered by a `ToolBlock` policy with `action =
require_approval` (instead of the default `block`). For example:

```json title="approval_policy.json"
{
  "name": "Outbound needs human review",
  "type": "ToolBlock",
  "scope": "Org",
  "config": {
    "tool_pattern": ["send_email", "stripe.charge"],
    "action": "require_approval"
  }
}
```

When the agent calls `send_email`, the gate pauses the call, creates
an approval row in the database, and notifies the configured alert
channels. The agent waits.

## What you see in the dashboard

The **Approvals** page lists every pending, approved, denied, and
expired request. Each row shows:

- The tool the agent wanted to call (e.g. `send_email`)
- The workflow that requested it
- How long ago it was created
- The risk level (set by your alert rules)
- The agent's reasoning (when the SDK provides it)

Click an approval to see the full context — what the agent was
trying to do, the tool's arguments (sanitised), and any notes you
attached.

## How to approve or deny

In the **Approvals** page, click an open request. You see:

1. The agent's goal (what it was trying to accomplish)
2. The tool it wants to call (e.g. `send_email`)
3. The arguments the agent wants to pass (e.g. recipient, subject)
4. How long the approval has been pending

Two buttons:

- **Approve** — the gate releases the reservation, the agent's call
  resumes, the LLM completes the tool call.
- **Deny** — the gate rejects, the agent sees `WorkflowKilledInterrupt`
  (a `BaseException`). The agent can catch it and clean up; most
  agents don't.

If you don't click either within the approval's `expires_at` window,
the request expires. The agent sees `WorkflowPausedException` (or the
gate equivalent) and can retry or give up.

## Notification channels

When an approval is created, the gateway notifies every active
channel configured on your org:

- **Email** — the default. Goes to every member with the
  `notify_on_approval_required` setting on.
- **Slack** — uses your org's installed Slack OAuth. Each org can
  install Slack once.
- **Webhook** — generic HTTPS POST with HMAC signature, useful for
  routing into PagerDuty or your own on-call rotation.

Disable a channel per-user under **Settings → Notifications**, or
per-channel under **Settings → Notification channels**.

## Programmatic approval (for automations)

The dashboard is for humans. If you want a CI bot or on-call rotation
to approve requests programmatically, the same endpoints are
exposed via REST:

```bash title="approve_via_api.sh"
curl -X POST "https://api.nullrun.io/api/v1/orgs/$ORG_ID/approvals/$APPROVAL_ID/approve" \
  -H "Authorization: Bearer $TOKEN"
```

The endpoint is idempotent — calling approve on an already-approved
request returns `409 approval_already_decided`. Use this in your
incident-response automation: an approval surfaces in Slack, your
bot detects the `risk_level = high`, and approves or denies based on
your runbook.

## When to use approval instead of blocking

Approval makes sense when:

- The operation is sensitive but **you want the agent to be able to
  do it** under human review (sending customer emails, creating
  invoices, deploying builds).
- The blast radius is bounded (a single email vs. an entire
  database drop).
- You have someone on-call who can review within minutes.

Blocking (not approval) makes more sense when:

- The operation is never legitimate (`db.drop` in a read-only
  workflow).
- The blast radius is unbounded (admin operations, mass deletes).
- No one is on-call to review approvals in time.

Approval is a feature, not a default. Most teams should default to
blocking and switch specific patterns to approval as the need
arises.

## What's logged

Every approval decision is in **Governance → Audit log**. You can
filter by:

- Approver (which user clicked Approve/Deny)
- Workflow
- Tool name
- Time window
- Outcome (approved / denied / expired)

The audit log is the source of truth for "who approved this?" — both
for compliance and for incident review.

## See also

- [Tool policies](tool-policies.md) — the `require_approval` action
- [Sensitive tools](sensitive-tools.md) — when approval isn't enough
- [Workflows → operator controls](workflow.md#how-to-control-one) —
  Pause / Kill work the same way as approval
- [API keys](api-keys.md) — how to mint a key bound to a workflow
