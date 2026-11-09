---
title: Notifications
maturity: stable
description: Where NullRun signals land — Slack and webhook channels, threshold rules, and the per-event switches that decide what each channel receives.
---

# Notifications

The **Notifications** page configures every outbound signal NullRun sends. It lives under **Notifications** in the sidebar.

Notifications are on Starter and above. On Lite the sidebar entry carries a lock, and the page shows an upgrade prompt.

The page has three sections:

1. **Channels** — where signals land.
2. **Alert rules** — thresholds that fire when a value crosses.
3. **Event subscriptions** — which events reach the channels.

The **Alerts** page is the read surface. Channels created here appear in the alert rules editor, and an alert that fires shows on both.

## Channels

Two channel types exist.

| Type | What it is |
|---|---|
| **Slack** | A Slack channel connected through the Slack app. |
| **Webhook** | A generic HTTPS endpoint that receives a JSON POST. |

There is no email channel, no PagerDuty channel, and no Discord channel.

### Adding a channel

Click **+ Add channel** and pick a type.

For a **webhook**, paste the HTTPS URL and give the channel a name. The signing secret is optional. With a secret set, every delivery carries three headers:

| Header | Meaning |
|---|---|
| `X-NullRun-Signature` | HMAC-SHA256 over the timestamp, the nonce, and the body, in that order. |
| `X-NullRun-Timestamp` | When the payload was signed. |
| `X-NullRun-Nonce` | A one-shot value that makes the delivery unique. |

A receiver should reject a timestamp that differs from its own clock by more than five minutes, and should remember a nonce for ten minutes. Compare the signature in constant time.

A channel marked test-only receives synthetic payloads only. Test payloads never reach a production destination.

### Send test

The **Send test** button on each channel card posts a synthetic payload and reports the outcome. Use it after creating or editing a channel, to confirm the endpoint delivers.

## Alert rules

A rule watches one value and fires when it crosses a threshold.

| Field | Meaning |
|---|---|
| **Type** | What the rule watches. |
| **Threshold** | The value that triggers the rule. Spend rules use cents. Error-rate rules use a count of events. |
| **Window** | How far back the rule looks, in minutes. |
| **Severity** | `info`, `warning`, or `critical`. The severity of the alert the rule produces. |
| **Enabled** | Whether the rule fires at all. |

The rule types are:

| Type | Watches |
|---|---|
| `daily_spend` | Spend over a day. |
| `hourly_spend` | Spend over an hour. |
| `error_rate` | The count of failed calls in the window. |
| `per_key_spend` | Spend by one API key. |

Each rule card shows the last value it observed against its threshold, and when it last fired.

## Event subscriptions

The matrix decides which events reach which channels. Each row is an event. Each column is a channel. A filled dot means the channel receives that event.

The events are:

| Group | Event | Fires when |
|---|---|---|
| Workflow activity | `execution_quota_warning` | The organization approaches its execution limit. |
| Workflow activity | `workflow_budget_warning` | A workflow exceeds its budget. |
| Workflow activity | `loop_detected` | A workflow makes repeated identical calls. |
| Workflow activity | `policy_violation` | An action is blocked by policy. |
| Workflow activity | `workflow_killed` | A workflow is terminated. |
| Governance & access | `approval_required` | A new approval is requested. Off by default. |
| Governance & access | `api_key_created` | An API key is created. |
| Team | `member_invite` | A new member is invited. |
| Digest | `daily_summary` | The previous day's activity digest. |
| Digest | `weekly_summary` | The previous week's activity digest. |

The toggle on the right of a row switches the event on or off for every channel. The dots are read-only indicators of where the event lands.

## API

The same actions are available over REST.

| Method | Path |
|---|---|
| `GET` | `/api/v1/orgs/{org_id}/alert-channels` |
| `POST` | `/api/v1/orgs/{org_id}/alert-channels` |
| `PATCH` | `/api/v1/orgs/{org_id}/alert-channels/{channel_id}` |
| `DELETE` | `/api/v1/orgs/{org_id}/alert-channels/{channel_id}` |
| `POST` | `/api/v1/orgs/{org_id}/alert-channels/{channel_id}/test` |
| `GET` | `/api/v1/orgs/{org_id}/alert-rules` |
| `POST` | `/api/v1/orgs/{org_id}/alert-rules` |
| `PATCH` | `/api/v1/orgs/{org_id}/alert-rules/{rule_id}` |
| `DELETE` | `/api/v1/orgs/{org_id}/alert-rules/{rule_id}` |
| `GET` | `/api/v1/orgs/{org_id}/notification-settings` |
| `PATCH` | `/api/v1/orgs/{org_id}/notification-settings` |

The plan gate is enforced on the server. A Lite organization cannot create a channel by calling the API directly.

## See also

- [Alerts](alerts.md) — what fired and what to do about it
- [Approvals](approvals.md) — where an approval request is announced
- [HTTP API](../reference/http-api.md) — the full endpoint catalog
