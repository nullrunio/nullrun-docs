---
title: FastAPI
description: Map NullRun gate refusals to HTTP status codes with the FastAPI integration.
maturity: stable
---

# Use with FastAPI

Install FastAPI next to the SDK.

```bash title="shell"
pip install nullrun fastapi uvicorn
```

`nullrun.integrations.fastapi.install(app)` registers the NullRun
exception handlers and the kill middleware on your app. Every refusal
the gate raises becomes a JSON response with an HTTP status.

```python title="fastapi_app.py"
import nullrun
from fastapi import FastAPI
from nullrun.integrations.fastapi import install

nullrun.init(api_key="nr_live_replace_me")

app = FastAPI()
install(app)


def run_agent(message: str) -> str:
    """Your agent call goes here."""
    return message


@app.post("/chat")
@nullrun.protect
def chat(message: str) -> dict:
    return {"reply": run_agent(message)}
```

## What `install()` registers

| Registration | Handles | HTTP |
|---|---|---|
| Exception handler for `NullRunDecision` | Budget, tool block, rate limit, pause, chain errors | Per `error_code` |
| Exception handler for `NullRunInfrastructureError` | Transport, backend, auth, config errors | `503` |
| ASGI middleware `NullRunMiddleware` | `WorkflowKilledInterrupt` | `503` |

The kill middleware sits outside the exception handler chain. A kill
that fires after the response has started cannot be rewritten, so the
middleware re-raises it and the connection drops.

## Status mapping for decisions

The integration reads `error_code` on the exception and picks a
status.

| `error_code` | HTTP | Meaning |
|---|---|---|
| `NR-B004` | `429` | Budget exhausted |
| `NR-L001` | `429` | Loop detected |
| `NR-R001` | `429` | Rate limit hit |
| `NR-T001` | `403` | Tool blocked |
| `NR-X001` | `403` | Generic block |
| `NR-W003` | `503` | Workflow paused |
| Any other decision code | `429` | Default |

Every infrastructure error maps to `503`.

The response carries a `Retry-After` header when the exception has a
`retry_after` value (rate limit) or a `resume_after` value (pause).

## Response body

```json
{
  "error_code": "NR-B004",
  "user_message": "You've reached the usage limit for this conversation. Please try again later.",
  "category": "decision",
  "retryable": false
}
```

| Field | Type | Meaning |
|---|---|---|
| `error_code` | string | Stable machine-readable code |
| `user_message` | string | End-user-safe text. Safe to render in a UI |
| `category` | `decision`, `infrastructure`, `killed` | Coarse class for client branching |
| `retryable` | bool | Mirrors the exception's own flag |

The kill response has no `retryable` field.

## Mapping one endpoint yourself

Use your own handler when an endpoint needs different wording or a
different status.

```python title="custom_mapping.py"
from fastapi import HTTPException
from nullrun import (
    NullRunDecision,
    NullRunInfrastructureError,
    WorkflowPausedException,
    format_user_message,
)


def run_agent(message: str) -> str:
    """Your agent call goes here."""
    return message


@app.post("/chat")
@nullrun.protect
def chat(message: str) -> dict:
    try:
        return {"reply": run_agent(message)}
    except WorkflowPausedException as exc:
        # .status_code is absent here. .resume_after carries the wait.
        raise HTTPException(
            status_code=503,
            detail={
                "message": format_user_message(exc),
                "code": exc.error_code,
            },
            headers={"Retry-After": str(int(exc.resume_after or 0))},
        )
    except NullRunDecision as exc:
        # .status_code is absent on some decision classes, so read it
        # defensively.
        raise HTTPException(
            status_code=getattr(exc, "status_code", None) or 403,
            detail={
                "message": format_user_message(exc),
                "code": exc.error_code,
                "retryable": exc.retryable,
            },
        )
    except NullRunInfrastructureError as exc:
        raise HTTPException(
            status_code=getattr(exc, "status_code", None) or 503,
            detail={"message": format_user_message(exc), "code": exc.error_code},
        )
```

Two classes carry no `status_code` attribute: `WorkflowPausedException`
and `WorkflowKilledInterrupt`. Read the attribute with `getattr` and
supply your own fallback.

## Per-deployment wording

Brand the message for one error code with `set_user_message`:

```python
import nullrun

nullrun.set_user_message(
    "NR-B004",
    "This workflow is out of budget. Raise the cap in the dashboard.",
)
```

## Two things to know

**Handler precedence follows the class hierarchy.** Starlette looks up
a handler by walking the exception's class hierarchy. A handler you
register for `NullRunError` therefore loses to the handlers
`install()` registers for `NullRunDecision` and
`NullRunInfrastructureError`. Register your own handler for one of
those two classes if you want to take it over.

**The kill is an `Exception`.** `WorkflowKilledInterrupt` derives from
`NullRunError`, so a blanket `except Exception:` in your agent code
swallows an operator kill. Catch `WorkflowKilledInterrupt` first and
re-raise.

```python title="kill_handling.py"
from nullrun import WorkflowKilledInterrupt


def run_agent(message: str) -> str:
    """Your agent call goes here."""
    return message


@app.post("/chat")
@nullrun.protect
def chat(message: str) -> dict:
    try:
        return {"reply": run_agent(message)}
    except WorkflowKilledInterrupt:
        raise
```

## See also

- [Quickstart](../getting-started/quickstart.md)
- [Errors](../reference/errors.md)
