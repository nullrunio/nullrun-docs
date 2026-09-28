---
title: Approvals (UI surface)
maturity: stable
description: The terminal-feed approvals dashboard — pending rows, friction-level buttons, the click-to-Dialog detail, and the history tab.
---

# Approvals (UI surface)

The **Approvals** page is where a human reviews and decides every
`require_approval` decision the gate returns. It lives at
`/control-center/approvals` (sidebar badge counts pending requests)
and is gated by the `approvals` plan feature — Growth and above.

This page covers the **UI surface** — terminal-feed rows, the
friction-level approve flow, the click-to-Dialog detail panel, and
the history tab. The wire contract (action_digest, typed
predicates, plan-tier gating) lives in [Human approval](human-approval.md).
Programmatic decision-making (REST endpoints, idempotency, retry
semantics) is at the bottom of this page; the API reference is in
[HTTP API → approvals](../reference/http-api.md#approvals).

## Page layout — terminal feed

The pending queue renders as a **terminal feed**: hairline-divided
rows in the spirit of the audit log + terminal-window vocabulary,
not bordered cards. Each row reads as a continuous log line; the
operator's eye locks onto the icon-prefix marker before parsing the
rest of the row.

### Status prefix markers

The first character of every row is a marker that encodes status
and tone:

| Marker | Tone | Status |
|---|---|---|
| `●` | state-block | `pending` |
| `✓` | state-allow | `approved` (history tab) |
| `✗` | state-flag | `denied` (history tab) |
| `⌧` | fg-muted | `expired` / `consumed` (history tab) |

### Row anatomy

From left to right:

1. **Prefix marker + workflow name + actor label** ("requested by X").
2. **Hero amount** — for money-kind approvals, the spend line is
   on the row with the ▲ N× above $X limit relationship encoder
   so the operator sees both the value and why it's over the
   limit in one glance. Tabular-nums at 28px semibold.
3. **Why this needs approval** — the rule label, deep-linkable to
   the rule's config page.
4. **Inline live countdown** — a colour-shifting bar + pipe +
   tabular `mm:ss` label that shrinks as the review window runs
   out. Colour flips green → amber → coral at 40% / 15% of the
   remaining window.
5. **Action button(s)** — see below.

For **tool-call approvals** (money kind = `tool_call`), the hero
amount is replaced by the operator-approved tool name + the raw
parameter bag, so the operator sees exactly what the SDK is about
to run. The `action_digest` is the tamper-evident binding, not a
display artefact — the dashboard shows the bag verbatim, never
reconstructed from the digest.

When the SDK forwarded `tool_class="mcp"` annotations, the row
also renders a class badge (`MCP tool` / `builtin` / `custom` /
`unknown`) plus a chip row for `destructive`, `read-only`,
`open-world` (each chip shows `yes` / `no` / `unknown`).

## Friction-level approve flow

The action button label encodes the friction level — operators
never fire an action without seeing the value they are approving:

- **Low risk** → single-click `[ approve ]`.
- **Medium risk** → `[ approve ]` → `[ type 499.00 to confirm ]`.
- **High risk** → `[ approve ]` → `[ type 1,000.00 ]` →
  `[ type refund_customer to confirm ]`.

The amount being approved is surfaced inside the button label
itself, not only in the confirmation step. The deny path is a
single click on every risk level — see the human-approval page for
why deny is unconditional.

## Click-to-Dialog

Clicking anywhere on a row (outside the action button) opens a
Dialog with the full detail panel:

- Hero summary (amount / tool name + parameter bag).
- **Why this needs approval** — the matched rule's human-readable
  predicate (`amount ≥ $50 USD`, `ANY(amount ≥ 5000, region IN [EU,US])`).
- **Technical details** accordion — open by default. Rows:
  Action fingerprint, Execution ID, Rule + rule label, Tool
  patterns, Per-call threshold, Rule priority (lower = higher),
  Review window, Trust level chip (`typed impact` /
  `LLM-cost only`), Rule created, and the rendered Action
  predicate.

The Dialog intentionally has **no Approve / Deny controls** — the
friction-level flow lives on the row, and the Dialog is for
review, not decision.

## History tab

The history view is the same page at `?tab=history` — a tab strip
in the page header switches between **Pending** (default) and
**History**.

History rows are filtered to the last 30 days by default and
support the same search / status filters as the pending feed.
Resolved rows are grouped by outcome (`approved`, `denied`,
`expired`, `consumed`) with the same prefix-marker vocabulary
(✓ / ✗ / ⌧) so an operator can scan a week of decisions in one
glance.

### Bulk toolbar

A hairline-divided toolbar above the feed exposes **Approve all**
and **Deny all** when more than one row is selected. Both bulk
actions require the same friction-level confirmations as the
single-row flow.

## Page chrome

- **Plan gate** — the page itself renders a `TierGate` upgrade
  prompt for plans without the `approvals` feature. The sidebar
  link is also hidden for those plans.
- **SSE live update** — every new approval request lands in the
  feed within a few seconds without refresh; the badge count in
  the sidebar updates in lockstep.
- **Audit trail** — every approve / deny decision is recorded in
  the audit log (`Audit log` under **Governance**) with the
  decided_by UUID, decided_at timestamp, and the operator label
  (or `System` for server-side expiry).

## Programmatic approval

For CI bots and on-call rotations, the same endpoints are exposed
via REST and the page chrome has no opinion:

```bash title="approve_via_api.sh"
curl -X POST "https://api.nullrun.io/api/v1/orgs/$ORG_ID/approvals/$APPROVAL_ID/approve" \
  -H "Authorization: Bearer ***"

# Or deny explicitly
curl -X POST "https://api.nullrun.io/api/v1/orgs/$ORG_ID/approvals/$APPROVAL_ID/deny" \
  -H "Authorization: Bearer ***"
```

The full endpoint catalog — idempotency rules (`409
approval_already_decided`), the post-approval `/execute`
binding, and digest-mismatch drift cases — is in
[HTTP API → approvals](../reference/http-api.md#approvals).

## Where to read next

- [Human approval](human-approval.md) — wire contract, action
  digest, typed predicates, plan-tier gating.
- [HTTP API → approvals](../reference/http-api.md#approvals) —
  REST endpoints for programmatic decision-making.
- [Audit log](error-handling.md#audit-trail) — every decision
  lands in the hash-chained audit log; the operator + `decided_by`
  UUID + `decided_at` are searchable.

!!! info "Deep dive"

    The approval flow is two-phase. The gate returns
    `require_approval`, the operator decides, and the waiting SDK is
    resumed by a push once the decision lands. Each approval row is
    bound to a digest of the action payload it was raised for, and the
    post-approval execute re-check recomputes that digest and refuses
    any call that does not match. An approved grant therefore cannot be
    redirected at a different action before it is spent.

    A decision is applied atomically: the outcome and the consumption
    stamp move together, so no reader can observe a half-decided row.
    Approving releases the pending reservation and decrements the
    outstanding-approval count as part of the same operation. Rows are
    scoped to the organization when they are read, so an identifier
    belonging to another organization reads as absent rather than
    forbidden, and the response gives away nothing about whether it
    exists.

    Expiry runs on a sweep rather than on the reader clock. Pending
    rows past their window become expired and are attributed to the
    system; approved rows that are no longer usable are closed
    separately, and closing them preserves the original decider and
    timestamp so a later automated transition cannot overwrite an
    explicit human decision.

    The push to the waiting SDK is best-effort, and a missed push is
    recovered by a periodic reconciliation pass. Audit emission is
    also best-effort: a transient failure there never blocks the
    decision itself. The stored decision is a typed value rather than
    free text, and the friction level the operator had to clear is
    recorded alongside it. Denial is terminal, and the SDK raises
    `WorkflowKilledInterrupt`. The auto-consume path reports consumed,
    already-consumed, and not-approved distinctly, and the SDK treats
    all three as success.
