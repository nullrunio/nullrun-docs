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
- **Masked URL** in mono for webhook channels; Slack channels show
  the channel name. See the Email variant note below.
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

!!! note "Email variant"
    The Email channel type is not available in the dialog. The
    channel list may contain read-only rows from prior installs;
    new channels use Slack or Webhook.

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

## Deep dive

### Mechanism
Notification channels live in `backend/src/alert/`. Channel rows are persisted in `alert_channels`; the `ChannelType` enum (`backend/src/alert/models.rs:25-39`) is two-valued — `Slack` and `Webhook` — after P1-43 (2026-08-17) removed the `Email` variant because the email backends silently lost deliveries. Slack uses OAuth via `slack_installations.encrypted_bot_token`; webhook channels carry an optional HMAC secret. `AlertManager::send_alert` (`backend/src/alert/managers.rs:320`) is the dispatch entry — it loads enabled channels, then calls `persist_bridge_alert` (line 469) which writes the row to the `alerts` table, then rate-limits per `(org_id, detector_type)`, then delivers. The persist step is the ADR-037 §6 fix that closes the "fresh-install org with no channels sees zero rows" gap. Alert rules are evaluated by the cron worker (`backend/src/cron::run_alert_rule_check`), which calls `dispatch_rule_to_channels` (`backend/src/alert/dispatcher.rs`).

### Guarantees
- **Channel delivery atomicity**: `get_enabled_channels` reads `enabled = true` rows; `test_mode = true` channels are partitioned off (P1-26) so real detector emissions never reach channels flagged as test-only.
- **Per-detector rate limit**: Redis key `alert:ratelimit:{org_id}:{detector_type}:{window}` enforces 1 alert per 15-minute window per org (one bucket per detector kind).
- **HMAC webhook integrity**: outgoing webhooks carry `X-NullRun-Signature`, `X-NullRun-Timestamp`, `X-NullRun-Nonce`; the canonical signing string is `<unix_ts>.<nonce>.<body>` and `HMAC-SHA256(secret, payload)` is computed in constant time (`backend/src/alert/webhook_signing.rs:7-11`).
- **Replay defence**: 5-minute clock-skew tolerance + 10-minute Redis nonce TTL — the ledger TTL matches the timestamp-drift window so the ledger can never outlive a valid timestamp.
- **Fail-CLOSED on notification_settings lookup**: a DB transport error opts the org out (silent opt-out) rather than amplifying during a DB blip (`backend/src/alert/bridges.rs:49-60`); the `record_alert_skipped_db_unavailable` counter surfaces the degraded mode.
- **Audit row always written**: `persist_bridge_alert` runs BEFORE the empty-channels early-return, so even an org with zero channels sees the row on `/alerts` — this is the load-bearing placement (lines 343-376).

### Patterns
- **Per-org opt-out flags**: `notification_settings.notify_on_workflow_killed`, `notify_on_approval_required`, etc. are checked by each bridge before constructing the `AlertPayload`. NULL row reads as `TRUE` (default-on); a DB error reads as `false` (fail-CLOSED).
- **Slack shape**: Slack incoming webhooks accept POST JSON, so no Block Kit transform is applied — the same generic JSON body lands in both Slack and Webhook channels.
- **Channel test**: `POST /api/alert_channels/{id}/test` posts a synthetic payload; the response surfaces the backend error per channel.
- **Bridge dispatch is fire-and-forget**: bridge dispatchers `tokio::spawn` so the calling site stays synchronous — failures are best-effort and never block the producer (`backend/src/alert/bridges.rs:80`).

### Approaches
The `Email` channel was removed (P1-43) because SendGrid required explicit opt-in and SES/SMTP were permanent stubs returning `Err`; operators saw deliveries silently lost. The Postgres `alert_channels.channel_type` column kept the `text` type (not ENUM) precisely so old `email` rows parse to `Err("Unknown channel type")` rather than being silently re-promoted to another type — surfaced as 400 on PATCH.

The Slack + Webhook pair was chosen because Slack's incoming-webhook shape accepts JSON out of the box (no Block Kit required) and webhook covers arbitrary HTTPS receivers with HMAC verification for the operator who needs PagerDuty / Datadog / oncall rotation. Legacy `pagerduty` / `discord` aliases were removed in Y-3 because they silently downgraded to Slack-shaped Block Kit JSON and never triggered the upstream incident.

### Limitations
- **Two channel types only**: Slack + Webhook. No native email / SMS / PagerDuty / Discord; legacy aliases (`email`, `pagerduty`, `discord`) surface as explicit `Err` on read.
- **Pre-existing `email` DB rows are read-only**: the read path returns `Err`, the write path returns 400; an operator must delete + re-create as `slack` / `webhook`.
- **Rate-limit bucket is per-detector coarse**: bursts of different alerts sharing a `detector_type` collapse to 1 per 15 minutes per org.
- **Webhook receiver clock-skew window is fixed at 5 minutes**: receivers with more than 5-minute clock drift from the sender silently drop the signature check; the receiver MUST verify `X-NullRun-Timestamp` drift before recomputing the signature.
