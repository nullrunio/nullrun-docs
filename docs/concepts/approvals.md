---
title: Approvals
maturity: stable
description: The operator review surface — what a pending request shows, how to approve or deny it, what expiry does, and what the agent sees next.
---

# Approvals

An **approval** is a tool call that an agent wants to make and a human has to authorise. The call parks until an operator decides, and the operator sees it on the **Approvals** page.

The approvals feature is on Growth and above. On a lower plan the sidebar entry carries a lock, and the page shows an upgrade prompt.

This page covers the review surface: what a request shows, how to decide, and what the agent sees afterwards. The rule format, the typed predicates, the digest binding, and the wire contract live in [Human approval](human-approval.md).

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

Click a row to open the full detail: the request id, the action fingerprint, the execution id, the rule, the tool patterns, the per-call threshold, the rule priority, the review window, the rule creation time, and the rendered predicate.

## Approving

The **Approve** button opens a **Confirm approval** dialog. The agent stays blocked until the operator confirms in the dialog.

| Risk | What the operator does |
|---|---|
| **LOW** | Click **Approve**, then **Confirm**. |
| **MEDIUM** | Click **Approve**, type the amount, then **Confirm**. |
| **HIGH** | Click **Approve**, type the amount, then **Continue**, type the action label, then **Confirm**. |

A request with no money amount has no amount to type. MEDIUM and HIGH requests then confirm on the action label alone. The action label is the tool name, or the action when the request carries no tool.

On approve, the grant is released and the agent resumes.

## Denying

Deny takes the same path at every risk level. The operator types a reason for the denial, then confirms with **Confirm Deny**.

The agent raises `NullRunApprovalDeniedError` (`NR-A011`) and the call does not run.

## Expiry

Every approval carries a review window, set by the rule that fired. When the window closes with no decision, the request expires and the agent raises `NullRunApprovalExpiredError` (`NR-A012`).

An approval never resolves silently. The operator has to click.

## How the grant binds to the payload

A grant is for one exact action, not for a tool name.

The gate stores a SHA-256 digest of the action's impact payload on the approval row. On the call that follows an approval, the gate recomputes the digest from the live payload and compares it with the approved one. The comparison is atomic, so two concurrent re-checks cannot both spend the same grant.

A changed amount, a changed argument, or a changed tool name breaks the digest, and the call is refused. The refusal codes and the wire contract are in [Human approval](human-approval.md).

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

A CI bot or an on-call rotation decides through the REST endpoints — see [HTTP API → approvals](../reference/http-api.md#approvals). An already-decided request answers `409 APPROVAL_ALREADY_DECIDED`; the codes are in [Error codes](../reference/errors.md).

## Audit trail

Every approve and deny lands in the audit log with the operator, the decision, the timestamp, and the execution id. The audit log is a plan feature: on Lite and Starter no row is written.

## See also

- [Human approval](human-approval.md) — approval rules, typed predicates, and the wire contract
- [Tool policies](tool-policies.md) — blocking a tool outright
- [Notifications](notifications.md) — where an approval request is announced
- [HTTP API → approvals](../reference/http-api.md#approvals) — the REST endpoints
