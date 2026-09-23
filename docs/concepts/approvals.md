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
   back on the row (reverted to inline from the dialog-only
   placement) with the ▲ N× above $X limit relationship encoder
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
- **Technical details** accordion — open by default after
  2026-08-31, because the closed chevron alone failed to signal
  that the rule_id / digest / execution_id rows lived behind the
  disclosure. Rows: Action fingerprint, Execution ID, Rule +
  rule label, Tool patterns, Per-call threshold, Rule priority
  (lower = higher), Review window, Trust level chip
  (`typed impact` / `LLM-cost only`), Rule created, and the
  rendered Action predicate.

The Dialog intentionally has **no Approve / Deny controls** — the
friction-level flow lives on the row, and the Dialog is for
review, not decision.

## History tab

The history view is the same page at `?tab=history` — a tab strip
in the page header switches between **Pending** (default) and
**History**. Old `/approvals/history` URLs redirect to
`?tab=history` so existing links keep working.

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
binding, and the digest-mismatch drift cases (`NR-A013` /
`NR-A014`) — is in
[HTTP API → approvals](../reference/http-api.md#approvals).

## Where to read next

- [Human approval](human-approval.md) — wire contract, action
  digest, typed predicates, plan-tier gating.
- [HTTP API → approvals](../reference/http-api.md#approvals) —
  REST endpoints for programmatic decision-making.
- [Audit log](error-handling.md#audit-trail) — every decision
  lands in the hash-chained audit log; the operator + `decided_by`
  UUID + `decided_at` are searchable.

## Deep dive

!!! info "Deep dive"

    Every approval decision flows through
    `backend/src/proxy/http/approvals.rs` (`approve_handler`) and
    `deny_handler`. Both extract the operator identity via
    `extract_session_user_id` (P0-19 /
    DEF-ARFLOW-DECIDED-BY-01), then call
    `ApprovalService::approve_with_method` or `approve` on
    `SqlxApprovalRepository`. On success, `approve_handler` releases
    the Redis envelope + decrements the pending-approval counter
    (`compensate_envelope_and_counter`), then publishes
    `EventBus::publish_approval_resolved` (`event_bus.rs`). The
    publish fans out via both in-process broadcast (subscriber on
    the same replica) and Redis pub/sub on
    `event_bus:approval_resolved` (cross-replica fan-out, ADR-023
    P0-3). On the receiving side,
    `ws_control.rs:convert_envelope_to_ws_message` converts the
    envelope to `WsMessage::ApprovalResolved { outcome, note, ... }`
    and pushes it to the parked SDK agent. The auto-consume path
    (ADR-047) lives at
    `backend/src/proxy/http/approvals.rs`
    (`consume_approval_handler`) — it accepts an `approval_id` and
    `organization_id` from the body, runs the atomic
    `consume_approved_by_id_only` SQL UPDATE, and returns one of
    `consumed` / `already_consumed` / `not_approved` (all 200 OK —
    the SDK treats all three as success). The expiry sweeper
    (`backend/src/workers/approval_expiry.rs:run_sweep`) cycles
    PENDING rows past `expires_at` to `EXPIRED` (system-decider
    discriminator `decided_by_kind = 'system_expiry'`, ADR-043)
    and APPROVED+stale rows to the new `REVOKED` status
    (ADR-056).

    The approval row's `expires_at` is set at creation time from the
    matched rule's `expires_in_seconds` (default 300s, per-rule
    override at `db/mod.rs`) — backend is the source of truth, and
    the SDK reads `approval_timeout_seconds` off the `/check`
    response (`backend/src/enforcement/gate_wire_adapter.rs`). The
    approve handler's atomic UPDATE mirrors the legacy NR-001 audit
    fix: status + `consumed_at` flip in a single SQL statement so
    the `chk_consumed_at_status` constraint never observes a
    half-stamped row. Cross-org IDOR is blocked at the SQL layer
    (`service.get_approval(org_uuid, approval_uuid)`) — the repo
    returns `None` on cross-org and the handler 404s with no
    existence leak. Decision emission through `governance audit` is
    best-effort fire-and-forget
    (`emit_approval_decision_audit`, `approvals.rs`); a transient
    DB blip never blocks the HTTP 204. The `decision` field on the
    audit row is one of the typed `GovernanceDecision` variants
    (`Approved` / `Denied`) — never a free-text string. WS push is
    best-effort with the `/approval-state/reconcile` fallback (P1-4)
    recovering missed events on the next reconcile tick. Denial is
    terminal — the SDK raises `WorkflowKilledInterrupt` (denial =
    kill for the originating execution, `ws_control.rs`).

    The terminal-feed UI reads from
    `GET /api/v1/orgs/:org_id/approvals`
    (`backend/src/proxy/http/approvals.rs`) which renders rows in
    the new `ApprovalStatusWire` enum (`Pending` / `Approved` /
    `Denied` / `Expired` / `Consumed` / `Revoked`). The status
    enum's wire-collapse bug
    (DEF-APPROVAL-CONSUMED-WIRE-COLLAPSE) is closed: pre-fix the
    `From<ApprovalStatus>` impl collapsed `Consumed → Expired`,
    hiding whether the SDK reused an approved grant vs. the sweeper
    closed it. The friction-level buttons map to
    `confirmation_method` values written to
    `approvals.confirmation_method` and rendered verbatim
    (`single_click` / `type_amount` / `type_action_amount`). The new
    SDK auto-consume endpoint closes `APPROVED` rows on the success
    path of `mode="inline"` approvals, which previously left rows
    dangling past `expires_at` because the consume SQL was only
    reachable from the `/execute` orchestrator. The operator-cancel
    path closes rows through the spawned cancel step.

    The two-phase split (gate-returns-`require_approval` → operator
    decides → WS push → SDK resumes) was the chosen path over the
    alternative of "operator pre-approves a tool pattern" — the
    alternative would have made approvals policy-shaped (no
    per-action review). `action_digest` (ADR-006) binds every
    approval row to a SHA-256 of the `BusinessImpact` payload
    (`backend/src/proxy/gate/business_impact.rs`, prefixed with
    `b"nullrun/v1/business_impact:"`); the `/execute` re-check
    refuses any call whose recomputed digest doesn't match. The
    auto-consume endpoint (ADR-047) was added over the alternative
    of a sweeper job that closes stale APPROVED rows — the
    auto-consume closes them at the moment of truth (success path)
    instead of after `expires_at + 60s`, which would have left rows
    visible to operators as "Awaiting decision" for an extra
    minute. The REVOKED status (ADR-056) was chosen over reusing
    EXPIRED because the operator genuinely approved — overwriting
    `decided_by` would have violated the §10.1 terminal-state
    invariant and broken forensic convergence on `audit_events`.

    Approvals live behind the `approvals` plan feature (Growth+);
    the `TierGate` prompt is rendered for plans below that. The
    dashboard page is org-scoped via session cookie; SDK callers use
    the org-less `/api/v1/approvals/{approval_id}/consume` path
    because org identity is derived from the API key (no `{org_id}`
    segment, unlike `/approve` / `/deny`). `confirmation_method` is
    an unauthenticated audit-trail field — the server rejects
    control characters at the handler edge
    (`reject_control_chars_or_err`, `approvals.rs`) to close the
    audit-pollution class on the approval surface. The expiry
    sweeper has two cycles per tick (PENDING → EXPIRED and
    APPROVED+stale → REVOKED); the §10.1 retraction guarantees
    `decided_by` / `decided_at` are never overwritten on REVOKED.
    The WS push is opt-in via `?wait_for_approval=true` on the
    upgrade (`ws_control.rs`); without that flag the SDK falls
    back to the legacy poll-based resume path. Cross-replica fan-out
    is best-effort Redis pub/sub — a publish failure logs and is
    recovered by the next periodic reconcile, but the originating
    replica's in-process broadcast always fires (so the local SDK
    agent always sees the event).
