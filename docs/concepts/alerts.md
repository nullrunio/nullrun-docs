---
title: Alerts
maturity: stable
description: Severity-tiered alerts surfaced in the dashboard — what the four KPI tiles mean, the filter chips, the snooze and dismiss flows.
---

# Alerts

The **Alerts** page surfaces every operational signal the gateway
fires that the operator should look at — blocked incidents,
threshold breaches, system events. It lives at
`/control-center/alerts` and is gated by the `alerts` plan feature
(Starter and above). On Lite plans the sidebar link is hidden and
direct URLs render an upgrade prompt.

The page reads from the same `alerts` feed that drives the
sidebar bell badge (count next to **Alerts**), so dismissing or
snoozing on the page brings the badge in line immediately.

## Page header

The header reads **Alerts** with a running subtitle that breaks
down the live state:

```
12 active · 5 resolved · 3 critical · 6 warning · 2 info
```

Zero-count tiers collapse out of the subtitle so a clean org
shows just `0 active · 0 resolved` with no visual noise. The
counts come from the unified `AlertListMeta` payload (per
ADR-037) and always include the **info** tier alongside
critical and warning — all three severities surface to operators.

The header action is **Dismiss all (N)** when at least one active
alert exists; clicking it opens a confirmation Dialog
("Dismiss N active alerts? This action cannot be undone.") with
Cancel and the destructive confirm button.

## Metric strip — not a row of four cards

The four tiles above the filter chips are:

| Tile | Sub-line example |
|---|---|
| **Action sources** | `Add one to begin` / `registered or observed` |
| **Verified** | `3 unverified — verify now` (deep link to `?filter=unverified`) / `all sources verified` |
| **Tool calls** | `Last 30 days across all sources` |
| **Drift** | `Tools match the upstream catalog` / `4 verification pending — not drift` |

If the list is still loading, every tile shows `—` rather than
`0`, so the operator never confuses "I don't know yet" with "the
answer is zero".

## Filter chips — two orthogonal dimensions

Two filter dimensions run side by side above the list:

- **Severity** — `All` / `Critical` / `Warning` / `Info`.
- **Category** — `All` / `Prevented` / `System`.

Severity is applied client-side (small enum, response shape
unchanged); Category is also pushed to the server via
`useAlerts({ category })` so the wire doesn't even ship the
filtered-out rows. The combination of the two narrows the list
independently — `Critical + Prevented` is the typical "what
incidents did the breaker actually stop today" view.

## Alert row anatomy

Each row is an `AlertCard` rendered as a hairline-divided block.
The components from top to bottom:

- **Severity left-border** — critical/warning/info accent.
- **Icon-avatar** — incident type (Wallet for budget_block,
  ShieldAlert for tool_block, Gauge for spend thresholds).
- **Title + body** — structured for `budget_block` rows:
  "Projected vs budget" stats + a horizontal threshold bar
  (current spend over threshold_cents, live from the wire).
- **Timestamp + workflow name** — when the alert is workflow-
  scoped; system alerts omit the workflow chip.
- **Snooze dropdown** — `1h` / `4h` / `24h` / `3d` / `7d`. The
  snoozed row is hidden from the active list until the snooze
  expires; a "Snoozed until …" footer line plus a live countdown
  appears on the row while the snooze is active.
- **Dismiss** — single click, the row collapses into the
  Resolved section.

## Resolved section

Beneath the active list, a **Resolved today** section shows
dismissed alerts from the current calendar day. Each row renders
the same `AlertCard` with a `resolved` flag — icon, title, body,
but no Snooze / Dismiss actions. The resolved section is
collapsed automatically when there are no resolved alerts.

## How to wire up alerts

The **Set up alerts** button in the top-right of the header takes
the operator to **Notifications** (`/control-center/notifications`)
where they can:

- Add Slack, Email, or Webhook channels.
- Configure threshold rules (e.g. "spend reaches 80% of cap").
- Subscribe the org's events to the enabled channels.

The Alerts page is the **read** surface; Notifications is the
**configure** surface. They share the same wire, so a channel
that fires lands both in the page and in the channel that the
operator subscribed to.

## API hooks

For automations, the same actions are exposed via REST and are
mirrored in the audit log:

- `POST /api/orgs/alerts/{id}/snooze` — `{ hours: number }` body.
- `POST /api/orgs/alerts/dismiss-all` — dismiss every active
  alert for the org in one call. Use sparingly; the gateway
  still writes one audit row per dismissal.

The plan-tier gate (`alerts` feature) is enforced server-side on
every handler — a Lite user cannot dismiss alerts by hitting the
API directly even if the page itself doesn't render.

## Where to read next

- [Notifications](notifications.md) — how to add channels and
  subscribe events.
- [Audit log](error-handling.md#audit-trail) — every dismiss /
  snooze is recorded as an audit row.

!!! info "Deep dive"

    The Alerts page is served by the alerts HTTP handler.
    `GET /api/v1/orgs/:org_id/alerts` returns
    `{ data: AlertResponse[], meta: AlertListMeta }`. The wire
    shape `AlertListMeta` carries `total`, `critical_count`,
    `warning_count`, and `info_count` — all three severities
    surface per ADR-037. The `Alert` domain model defines
    `AlertSeverity = {Critical, Warning, Info}`, `AlertCategory`
    = `{Prevented, System}`. Alerts flow in from three producer
    groups: the `mirror_incident_to_alert` SQL trigger mirroring
    `prevented_incidents` (Prevented kind), System producers
    (spend thresholds 80/95/100; `api_key_revoked` classified
    as Warning), and bridge-mirrored System events.

    Severity classification is server-side: `api_key_revoked`
    is classified as Warning; the severity ladder (80/95
    Warning, 100 Critical) reserves Critical for hard-block
    signals. The plan-tier gate is server-side: `Feature::Alerts`
    is enforced on LIST, dismiss, snooze, and dismiss-all
    handlers; a Lite user cannot enumerate alerts by API bypass
    even though the dashboard link is hidden. Header counts
    match listed rows: `critical_count` / `warning_count` /
    `info_count` are scoped to the same `?category=` filter
    so the operator never sees a count that disagrees with
    what's on screen. Category invariant: System alerts MUST
    have `workflow_id = None` and `workflow_name = None`; the
    writer enforces before insert. Dismiss is idempotent:
    dismissing an already-dismissed alert is a no-op; every
    dismissal writes one audit row per ADR-009 four-table
    separation.

    The three-tier active set is
    `dismissed = false AND (snoozed_until IS NULL OR snoozed_until < now())`
    — the same predicate is reused by the three
    `count_active_by_severity` calls, so the `info_count` field
    reuses the active-set query. `?category=` rejects unknown
    values: the handler returns 400 with the supported set. The
    spend-threshold chip ladder is 80% Warning (`blue` tone
    chip), 95% Warning (`yellow` tone chip), 100% Critical
    (`red` tone chip) per ADR-037 §5; the wire shape is the
    same, only the frontend `AlertChip["tone"]` ladder.
    Severity × category are orthogonal: `prevented × critical`
    (budget_block) and `system × info` (member_invited) are
    both real combinations — severity is urgency, category
    is ownership (ADR-037 §2).

    ADR-037 codifies the `AlertIncidentKind` discriminated
    union on the frontend mirroring the whitelisted
    `incident_type` values from `prevented_incidents`, System
    titles (spend thresholds, `api_key_revoked`), and bridge-
    mirrored titles (`approval_required`, `workflow_state_change`,
    `loop_detected`, `policy_violation`, `member_invited`,
    `api_key_created`) plus catch-alls (`unrecognized`, `other`).
    The unified `ALERT_DESCRIPTORS` lookup table maps each
    kind to icon/label/chips/CTA. The taxonomy is enforced in
    three places that MUST stay aligned: the backend producer
    sites (the spend-threshold dispatcher, the API-key
    revocation site, the bridge dispatchers, the cron-rule
    dispatcher), the SQL mirror trigger
    (`prevented_incidents` → `alerts`), and the frontend
    `classifyAlert` classifier.

    Coarse severity enum (3 tiers): no "Investigate" or "Watch"
    tier between Warning and Info — the chroma ladder (`blue` /
    `yellow` / `red`) is the only in-band signal between them.
    Bridge rate-limit bucket of 1/15min/org per detector_type: a
    burst of bridge alerts sharing a `detector_type` collapses;
    rapid emissions are silently dropped at the channel layer.
    Dismiss-all is org-wide: no per-workflow dismissal path —
    the operator who wants workflow-scoped cleanup must dismiss
    row-by-row. The snooze trail is column-only: who-snoozed-
    when is in `alerts.snoozed_until` but the per-row snooze
    actor is not surfaced on the alerts view — only in the
    dedicated audit log.
