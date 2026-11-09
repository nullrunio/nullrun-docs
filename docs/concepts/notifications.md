---
title: Notifications
maturity: stable
description: Where NullRun signals land — the Slack and webhook channels that receive them, and the per-event switches that decide what each channel gets.
---

# Notifications

The **Notifications** page configures every outbound signal NullRun sends. It lives under **Account** in the sidebar.

Notifications are on Starter and above. On Lite the sidebar entry carries a lock, and the page shows an upgrade prompt.

The page has two sections:

1. **Alert channels** — where signals land.
2. **Event subscriptions** — which events reach the channels.

Threshold rules are a third piece of the model, and the control center has no editor for them. Rules are configured over the REST API. See [Alerts](alerts.md#threshold-rules).

## Alert channels

Two channel types exist.

| Type | What it is |
|---|---|
| **Slack** | A Slack App channel. It is bound to a Slack installation and a Slack channel, and posts through Slack's API with a bot token. |
| **Webhook** | A generic HTTPS endpoint that receives a JSON POST. |

The two types do not post the same payload. The Slack App connection is
set up separately, and the **Add channel** dialog does not offer it. A
Slack incoming webhook URL is saved as a **Webhook** channel.

The API accepts `slack` and `webhook` only. A third type is refused.

### Adding a channel

Click **Add channel** in the **Alert channels** section header and pick the type. The dialog asks for:

| Field | Meaning |
|---|---|
| **Name** | The label on the channel card and in alert messages. |
| **Webhook URL** | The HTTPS endpoint that receives the payload. |
| **Signing secret** | Optional. The key the receiver verifies the payload with. |
| **Test mode** | Suppress real alerts to this channel. |

With a signing secret set, every delivery carries four headers:

| Header | Meaning |
|---|---|
| `X-NullRun-Signature` | HMAC-SHA256 over `timestamp.nonce.body`. |
| `X-NullRun-Timestamp` | When the payload was signed. |
| `X-NullRun-Nonce` | A one-shot value that makes the delivery unique. |
| `X-NullRun-Event-Id` | The identifier of the event. |

A receiver should reject a timestamp that differs from its own clock by more than five minutes, and should remember a nonce for ten minutes. Compare the signature in constant time.

### Test mode

A channel in test mode receives synthetic payloads only. Real alerts do not reach it. The channel card carries a **Test mode** badge.

### Test send

**Test send** in the channel menu posts a synthetic payload and reports the outcome. The card shows **Test sent** or **Test failed**. Use it after creating or editing a channel, to confirm the endpoint delivers.

The card also shows the last delivery time, or **Never triggered**.

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

The toggle on the right of a row switches the event on or off for every channel. The dots are read-only indicators of where the event lands, and a disabled channel shows a dashed cell.

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
