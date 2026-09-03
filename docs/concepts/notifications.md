---
title: Notifications
maturity: stable
description: Alert channels (Slack / Email / Webhook), threshold rules, and the per-event subscription matrix that controls where every signal lands.
---

# Notifications

The **Notifications** page is the configure surface for every
outbound signal NullRun sends. It lives at
`/control-center/notifications` in the sidebar and is gated by the
Starter plan and above.

The page has three sections in this order:

1. **Channels** — where signals can land (Slack / Email / Webhook).
2. **Alert rules** — threshold rules that fire when a value crosses.
3. **Event subscriptions** — which events reach which channels.

It is the **configure** surface for [Alerts](alerts.md) (the read
surface); channels created here appear in the Alert rules editor,
and alerts dismissed on the Alerts page keep their wire-side
notification enabled.

## Channels

The top section is a 2-up grid of channel cards. Each card carries:

- **Icon tile** + **Channel name**.
- **Masked URL** in mono for webhook channels (Slack channels show
  the channel name; legacy email channels have been retired —
  see the migration note below).
- **Status dot** — neutral for idle, faint for `last_sent` (so
  the operator can see at a glance whether the channel has fired
  recently).
- **Edit link** + **Send test** icon-btn + **On / off** switch row.

### Adding a channel

Click **+ Add channel** in the section header. The dialog supports:

- **Slack** — OAuth-branded setup with Slack-specific help text.
  Pre-pivot rows that store `installation_id` / `channel_id` in
  config are preserved on edit so the existing connection
  doesn't break.
- **Webhook** — generic HTTPS POST. The signing secret is
  optional; if set, the receiver verifies `X-NullRun-Signature`
  (HMAC-SHA256, 5-minute clock-skew tolerance, 10-minute nonce
  replay defence).

Both Slack and generic webhook store on the backend as
`channel_type: "webhook"` with `config: { type: "webhook", url: ... }`
— Slack incoming webhooks accept POST JSON out of the box, so no
Block Kit transform is needed for MVP.

!!! note "Email variant removed"
    The Email channel type was removed on 2026-08-17 (P1-43) and
    is no longer available in the dialog. Legacy rows continue
    to render in the list but cannot be re-created.

### Send test

The **Send test** button on each card posts a synthetic payload
to the channel; the toast reports success or surfaces the
backend's error message. Use this after creating or editing a
channel to confirm your URL / OAuth installation actually
delivers before relying on it for production signals.

## Alert rules

The middle section is a list of threshold rules. Each rule
renders as a card with:

- **Left-border accent by severity** — info / warning / critical.
- **Inline gauge bar** showing `last_observed_value / threshold_cents`
  live from the wire.
- **Last-fired timestamp** + **enabled toggle** + **delete link** on
  the right.

Rule editing is a form inside an `AlertRulesSection` dialog. The
form shape mirrors the wire contract — name, severity, threshold in
cents, and which channels the rule routes to.

## Event subscriptions matrix

The bottom section is the matrix that decides which event reaches
which channel. Events are grouped by area:

- **Workflow activity** — `workflow.killed`, `workflow.paused`,
  `workflow.resumed`, `workflow.created`.
- **Governance & access** — `approval.created`, `approval.decided`,
  `policy.changed`, `key.created`, `key.revoked`.
- **Team** — `member.invited`, `member.joined`, `member.removed`.
- **Digest** — weekly spend digest, monthly quota report.

Each event is a row; each channel is a column. A cell shows a
chip-dot when the event is enabled for that channel; no chip means
the event is disabled for that channel. The right edge of each row
has a master on/off toggle that flips every channel at once.

A footer legend explains the chip-dot semantics (`●` = enabled, no
chip = disabled).

## Plan gating

The Notifications page itself renders a `TierGate` upgrade prompt
for plans without Starter; the sidebar link is also hidden. The
upgrade card links to **Billing & Plan** (`/control-center/billing`)
and to the public pricing page (which hosts the comparison table)
so operators can inspect feature deltas before committing.

The plan-tier gate is enforced server-side on every
`/api/alert_channels` and `/api/alert_rules` handler — a Lite user
cannot POST to the API directly even if the page itself doesn't
render.

## API hooks

For automations, the same actions are exposed via REST:

- `GET /api/alert_channels` / `POST` / `PATCH /{id}` / `DELETE /{id}`.
- `POST /api/alert_channels/{id}/test` — fire a synthetic payload.
- `GET /api/alert_rules` / `POST` / `PATCH /{id}` / `DELETE /{id}`.

The full endpoint catalog is in
[HTTP API → alert channels](../reference/http-api.md) (and the
alert-rules section, when split out).

## Where to read next

- [Alerts](alerts.md) — the read surface for what fired.
- [Audit log](error-handling.md#audit-trail) — every channel and
  rule mutation is recorded as an audit row.
