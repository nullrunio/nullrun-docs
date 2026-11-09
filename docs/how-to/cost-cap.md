---
title: Hard cost cap
description: Set a per-workflow budget cap, and see what the SDK raises when the cap is reached.
maturity: stable
---

# Set a hard cost cap

A cost cap stops an agent from spending past a number you chose. The cap
is per workflow and per billing period.

The gateway enforces the cap. The SDK asks the gateway before every
protected call and books the real cost after the call returns.

## Set the cap

In the dashboard: open the workflow, choose **Settings**, set **Budget**
in cents, and save. `$50.00` is `5000`.

Over the HTTP API, `PATCH` the workflow:

```bash title="shell"
ORG_ID=8a3b1c7d-0000-4000-8000-000000000000
WORKFLOW_ID=1f2e3d4c-0000-4000-8000-000000000000
API_KEY=nr_live_replace_me

curl -sS -X PATCH \
  "https://api.nullrun.io/api/v1/orgs/$ORG_ID/workflows/$WORKFLOW_ID" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"budget_cents": 500}'
```

`budget_cents` is the only field the request needs. A cap of `0` means
no per-workflow cap — the call passes through to the organization cap.

The key must belong to the organization in the path. The caller also
needs the Admin role, and the key must be bound to a user. A dashboard
session works too: replace the `X-API-Key` header with
`Authorization: Bearer $SESSION_TOKEN`. See
[HTTP API → Authentication](../reference/http-api.md#authentication).

## Run against the cap

```python title="budgeted_run.py"
import nullrun
from nullrun import init, protect

init(api_key="nr_live_replace_me")


def call_model(question: str) -> str:
    """Your model call goes here."""
    return question


@protect
def answer(question: str) -> str:
    return call_model(question)
```

| Refusal | Exception | `error_code` |
|---|---|---|
| Budget cap reached | `NullRunBudgetError` | `NR-B004` |
| Tool blocked by policy | `NullRunToolBlockedError` | `NR-T001` |

Both are subclasses of `NullRunBlockedException`, so one
`except NullRunBlockedException` clause catches both. The typed subclass
carries the specific `error_code`. See [Errors](../reference/errors.md).

## How the cap is checked

Each protected call runs the gate first:

1. The gateway reserves the projected cost of the call.
2. If the reservation crosses the cap, the call is refused and nothing
   is reserved.
3. After the call returns, the gateway books the real cost against the
   reservation.

The real cost may exceed the reservation by a small fixed amount. A
booking above the reservation plus that amount is rejected. The commit
answers `422` with the wire code `CONSUME_OVERBUDGET`, and the SDK
raises `NullRunConsumeOverbudgetError` (`NR-O001`). See
[Budgets → Reserve and consume](../concepts/budgets.md#reserve-and-consume).

The SDK does not compute the cost. It sends the model and a token
estimate to the gate. After the call it sends the token counts the
provider reported. The gateway prices the call.

## Soft mode

A policy set to **Soft** lets the agent run past the cap while a chain
is active, up to an overdraft limit. Soft mode needs all three of: the
policy sets `enforcement_mode` to `Soft`, an active chain exists, and
the projected cost stays inside the overdraft limits. When one of them
is missing, the budget behaves as Hard. See
[Policies → BudgetLimit extra fields](../concepts/policies.md#budgetlimit-extra-fields)
and [Policies → Soft mode requirements](../concepts/policies.md#soft-mode-requirements).

## See also

- [Budgets](../concepts/budgets.md) — periods, spend, and the reserve
- [Errors](../reference/errors.md) — the full exception catalog
- [Examples → cost cap demo](https://github.com/nullrunio/nullrun-examples/blob/master/examples/cost_cap_demo.py)
