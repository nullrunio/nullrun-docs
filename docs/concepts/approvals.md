---
title: Approvals
maturity: stable
description: The operator-facing side of approvals — what a pending request shows, how to approve or deny it, what expiry does, and how a grant binds to the exact payload.
---

# Approvals

An **approval** is a tool call that an agent wants to make and a human has to authorise. The call parks until an operator decides, and the operator sees it on the **Approvals** page.

The approvals feature is on Growth and above. On a lower plan the sidebar entry carries a lock, and the page shows an upgrade prompt.

This page covers the review surface: what a request shows, how to decide, and what the agent sees afterwards. The rule format, the typed predicates, and the wire contract live in [Human approval](human-approval.md).

## What a pending request shows

Each pending row carries:

| Field | What it tells you |
|---|---|
| **Tool and arguments** | The exact tool the agent wants to call and the arguments it wants to pass. |
| **Why it needs approval** | The rule that matched, in plain language. |
| **Risk** | `LOW`, `MEDIUM`, or `HIGH`. |
| **Time left** | How long the operator has to decide. |
| **Workflow** | The workflow that raised the request. |

The pending feed refreshes every 30 seconds, and the badge next to **Approvals** in the sidebar carries the pending count.

Click a row to open the full detail: the action fingerprint, the execution id, the rule, the tool patterns, the threshold, the review window, and the rendered predicate.

## Approving

The approve button names the amount or the action, so nobody approves a value they cannot see.

| Risk | What the operator does |
|---|---|
| **LOW** | Click **Approve**. |
| **MEDIUM** | Click **Approve**, then type the amount. |
| **HIGH** | Click **Approve**, then type the amount, then type the action label. |

A request with no money amount has no amount to type. MEDIUM and HIGH requests then confirm on the action label alone. The action label is the tool name, or the action when the request carries no tool.

On approve, the grant is released and the agent resumes.

## Denying

Deny takes the same path at every risk level. The operator types a reason for the denial, then confirms it.

The agent raises `NullRunApprovalDeniedError` (`NR-A011`) and the call does not run.

## Expiry

Every approval carries a review window, set by the rule that fired. When the window closes with no decision, the request expires and the agent raises `NullRunApprovalExpiredError` (`NR-A012`).

An approval never resolves silently. The operator has to click.

## How the grant binds to the payload

An approval is a grant for one exact action, not for a tool name.

When the request is raised, the gate computes a SHA-256 digest of the action's impact payload and stores it on the approval row. On the call that follows an approval, the gate recomputes the digest from the live payload and compares it with the approved one. The comparison is atomic, so two concurrent re-checks cannot both spend the same grant.

| Situation | Result |
|---|---|
| The payload matches | The grant is consumed and the call proceeds |
| The impact payload changed | Refused, `NR-A013` |
| The tool digest changed | Refused, `NR-A014` |
| The grant was already consumed | Refused, `NR-A015` |

A changed amount, a changed argument, or a changed tool name all break the digest. The operator approved that amount and those arguments, and nothing else.

## History

The **History** tab holds the whole approval record. It has two sections:

| Section | Rows |
|---|---|
| Awaiting decision | Requests with no decision yet. |
| Decided | Requests that were approved, denied, expired, or consumed. |

The search box filters the rows by workflow, action, tool, reason, actor, or comment. The filter is part of the URL, so a filtered history can be shared as a link.

## Deciding in bulk

The toolbar above the pending queue counts the low-risk pending requests that are eligible for a bulk action. **Approve all N** opens a confirmation that lists each request. Nothing is sent until the operator confirms.

Medium- and high-risk requests are not eligible for a bulk approval. Each one takes its own type-to-confirm step.

## Programmatic approval

A CI bot or an on-call rotation can decide through the same endpoints:

```bash title="approve_via_api.sh"
curl -X POST "https://api.nullrun.io/api/v1/orgs/$ORG_ID/approvals/$APPROVAL_ID/approve" \
  -H "Authorization: Bearer $NULLRUN_API_KEY"

# Or deny explicitly
curl -X POST "https://api.nullrun.io/api/v1/orgs/$ORG_ID/approvals/$APPROVAL_ID/deny" \
  -H "Authorization: Bearer $NULLRUN_API_KEY"
```

Deciding twice is not an error. Approving a decided request returns `409 APPROVAL_ALREADY_DECIDED`.

## Audit trail

Every approve and deny lands in the audit log with the operator, the timestamp, and the outcome. The action digest on the row proves which payload the operator approved.

## See also

- [Human approval](human-approval.md) — approval rules, typed predicates, and the wire contract
- [Tool policies](tool-policies.md) — blocking a tool outright
- [Notifications](notifications.md) — where an approval request is announced
- [HTTP API → approvals](../reference/http-api.md#approvals) — the REST endpoints
