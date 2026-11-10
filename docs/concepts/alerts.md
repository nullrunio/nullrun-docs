---
title: Alerts
maturity: stable
description: The operational signals the gateway raises — what fires an alert, how to filter the feed, and how to snooze or dismiss one.
---

# Alerts

The **Alerts** page shows the signals an operator has to look at: a threshold the spend crossed, an action the gate stopped, an event about the organization.

Alerts are on Starter and above. On Lite the sidebar entry carries a lock, and the page shows an upgrade prompt.

The page reads the same feed as the badge next to **Alerts** in the sidebar, so a dismiss or a snooze brings the badge in line.

## Reading the feed

The header carries one number per quantity:

```
3 active of 5 · 2 snoozed · 1 of 2 critical
```

| Part | Meaning |
|---|---|
| `3 active of 5` | Rows visible under the current filters, of the organization's active total. The second number appears when a filter narrows the view. |
| `2 snoozed` | Alerts that are open but snoozed. The table hides them. |
| `1 of 2 critical` | Visible critical alerts, of the organization's critical total. |

The header also offers **Dismiss all (N)**. N counts every open alert, snoozed included.

## Filters

| Filter | Values |
|---|---|
| **Severity** | All, Critical, Warning, Info |
| **Source** | All, Prevented, System |
| **State** | All, Active, Digests |

**Prevented** alerts are the ones the gate stopped: a tool block, a budget block. **System** alerts are about the organization: a spend threshold, a killed workflow, a revoked key.

Severity and source are independent. A prevented incident can be critical, and a system event can be informational.

## A row

Each row shows the severity, what happened, the workflow it belongs to, and when it happened. Two actions:

| Action | Effect |
|---|---|
| **Snooze** | Hides the row for 1 hour, 24 hours, or 7 days. The row shows a countdown until it returns. |
| **Dismiss** | Closes the alert. It moves to the resolved list. |

Beneath the active list, a **Resolved today (N)** section holds the alerts dismissed during the current day. Dismissed rows carry no actions.

## What raises an alert

### Threshold rules

Threshold rules are configured over the REST API. The control center has no editor for them: the **Notifications** page carries channels and event subscriptions, and nothing else.

Each rule has:

| Field | Meaning |
|---|---|
| **Name** | The label on the rule and in the alert it produces. |
| **Type** | What the rule watches. |
| **Threshold** | The value that triggers the rule. Spend rules use cents. Error-rate rules use a count of events. |
| **Window** | How far back the rule looks, in minutes. Defaults to 60. |
| **Severity** | `info`, `warning`, or `critical`. The severity of the alert the rule produces. Defaults to `warning`. |
| **Enabled** | Whether the rule fires at all. Defaults to on. |

The rule types are:

| Type | Watches |
|---|---|
| `daily_spend` | Spend over a day. |
| `hourly_spend` | Spend over an hour. |
| `error_rate` | The count of blocked and denied decisions in the window. |
| `per_key_spend` | Spend by one API key. |

A rule does not fire again within 15 minutes of its last firing. Each rule carries the last value it observed and when it last fired.

### The budget ladder

Running spend raises alerts at three fixed points:

| Spend | Severity |
|---|---|
| 80% of the threshold | Warning |
| 95% of the threshold | Warning |
| 100% of the threshold | Critical |

The threshold is a number read from your plan's limits, compared against the
organization's spend in cents. It is not the cap of a `BudgetLimit` policy,
so a policy cap and the alert ladder can fire at different times.

### Events

The event subscriptions on the **Notifications** page decide which events reach your channels. The full list is in [Notifications](notifications.md#event-subscriptions).

## Configuring alerts

The **Set up alerts** button in the header opens the **Notifications** page, where you add the channels that receive the signals. The Alerts page is the read surface; Notifications is the configure surface. They share the same feed, so an alert that fires shows on both.

## API

| Method | Path |
|---|---|
| `GET` | `/api/v1/orgs/{org_id}/alerts` |
| `POST` | `/api/v1/orgs/{org_id}/alerts/{alert_id}/snooze` — body `{"hours": 24}`, clamped to 1–168 hours. |
| `POST` | `/api/v1/orgs/{org_id}/alerts/{alert_id}/dismiss` |
| `POST` | `/api/v1/orgs/{org_id}/alerts/dismiss-all` |

Dismiss-all covers the whole organization. There is no per-workflow bulk path, so cleaning up one workflow means dismissing its rows one by one.

The alert rules use their own paths. See [Notifications → API](notifications.md#api).

## See also

- [Notifications](notifications.md) — channels and event subscriptions
- [Budgets](budgets.md) — the spend behind a spend alert
- [Policies](policies.md) — what produces a blocked action
