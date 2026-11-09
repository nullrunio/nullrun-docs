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

You write these on the **Notifications** page. Each rule watches one value in a window.

| Rule type | Watches |
|---|---|
| `daily_spend` | Spend over a day. |
| `hourly_spend` | Spend over an hour. |
| `error_rate` | The count of failed calls in the window. |
| `per_key_spend` | Spend by one API key. |

A rule has a threshold, a window in minutes, a severity, and an enabled switch. A spend rule uses cents. An error-rate rule uses a count of events.

### The budget ladder

Spending against a monthly budget raises alerts at fixed points:

| Spend | Severity |
|---|---|
| 80% of the budget | Warning |
| 95% of the budget | Warning |
| 100% of the budget | Critical |

### Events

The event subscriptions on the **Notifications** page decide which of these reach your channels and which show on this page:

- Approaching the execution limit.
- A workflow over its budget.
- A workflow making repeated identical calls.
- An action blocked by policy.
- A workflow terminated.
- An API key created.
- A member invited.

## Configuring alerts

The **Set up alerts** button in the header opens the **Notifications** page, where you add channels and write rules. The Alerts page is the read surface; Notifications is the configure surface. They share the same feed, so an alert that fires shows on both.

## API

| Method | Path |
|---|---|
| `GET` | `/api/v1/orgs/{org_id}/alerts` |
| `POST` | `/api/v1/orgs/{org_id}/alerts/{alert_id}/snooze` — body `{"hours": 24}`, clamped to 1–168 hours. |
| `POST` | `/api/v1/orgs/{org_id}/alerts/{alert_id}/dismiss` |
| `POST` | `/api/v1/orgs/{org_id}/alerts/dismiss-all` |

Dismiss-all covers the whole organization. There is no per-workflow bulk path, so cleaning up one workflow means dismissing its rows one by one.

## See also

- [Notifications](notifications.md) — channels and rules
- [Budgets](budgets.md) — the spend behind a spend alert
- [Policies](policies.md) — what produces a blocked action
