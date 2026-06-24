# Troubleshooting

What to expect when NullRun is doing its job — and how to recover
when it isn't.

## What can go wrong (and how NullRun reacts)

| Situation | Default behaviour | Exception raised |
| --- | --- | --- |
| Workflow exceeds budget | Halt at next `@protect` call | `NullRunBlockedException` (or `NullRunBudgetError` for the catalogue code) |
| Agent stuck in a loop | Halt at next `@protect` call | `NullRunBlockedException` |
| Agent calls a sensitive tool | Block the call before the function body runs | `NullRunBlockedException` (or `NullRunToolBlockedError`) |
| Gateway unreachable, normal tool | Allow (PERMISSIVE fallback) | (none — call proceeds) |
| Gateway unreachable, sensitive tool | **Fail closed** — block the call | `NullRunBlockedException` |
| Workflow killed via dashboard | Raise at next `@protect` call (or pre-request for in-flight LLM calls) | `WorkflowKilledInterrupt` (`BaseException`) |
| Workflow paused via dashboard | Raise at next `@protect` call | `WorkflowPausedException` |
| Missing `api_key` on `init()` | Raise at first SDK call | `NullRunAuthenticationError` |
| HMAC signature missing / stale | Reject the request (401) | `NullRunAuthenticationError` |
| Plan monthly / per-dimension cap reached | Reject the request (**422** with `error=plan_limit_exceeded` or `workflow_limit_reached`; `details.resource` names the dimension) | `NullRunBlockedException` |
| Per-minute rate cap reached | Reject the request (429 with `Retry-After`) | `RateLimitError` |
| `workflow_id` paused / killed (WS push) | Apply at next `@protect` call | `WorkflowKilledInterrupt` / `WorkflowPausedException` |
| `Policy.fetch` fails on first call | Use cached policy → fall back to `Policy.strict_local()` (zero budget, 1-call rate limit) | (none — `track_event` returns the block verdict; no exception) |

> Fail-closed vs fail-open defaults live in `proxy/handlers.rs` and
> `policy/service.rs`. The full fail-CLOSED / fail-OPEN policy is
> documented in the project root `CLAUDE.md` — anything in the SDK
> that touches a billing or quota gate fails closed on transport
> error.

## Common runtime questions

### "Why is my call being rejected with `NullRunBlockedException`?"

The most common causes, in order of frequency:

1. **Budget exhausted** — your `policy.budget_cents` ran out. Either
   raise the cap in the dashboard or end the workflow.
2. **Loop detected** — same tool / same args called too many times in
   a short window. Inspect the workflow with
   `GET /api/v1/orgs/{org}/executions/{execution_id}` and adjust the
   loop policy in the policy editor.
3. **Sensitive tool blocked** — the function is marked `@sensitive`
   and the policy says `deny` for this workflow. Override with an
   approval rule, or remove the `@sensitive` decorator if the
   classification is wrong.

### "Why is my workflow paused / killed without me doing anything?"

Two usual suspects:

- **Dashboard action** — open the workflow's detail page; the audit
  log shows the actor and timestamp.
- **Stream-reservation auto-pause** — the per-reservation stream
  control loop pauses at 80% consumption and cancels at 95%
  (`StreamControlLoop::pause_threshold` / `cancel_threshold` in
  `backend/src/billing/reservation.rs`). This is per-stream, not
  per-plan-monthly — it fires inside a single LLM call once the
  reservation is mostly consumed. Resumable from the dashboard.

### "Why is the SDK raising `NullRunAuthenticationError`?"

- `NULLRUN_API_KEY` is unset or the key was revoked.
- `NULLRUN_SECRET_KEY` is unset and `NULLRUN_HMAC_REQUIRED=true`
  (the production default). Set both, or relax the policy.
- The HMAC clock skew is more than `NULLRUN_HMAC_MAX_AGE_SECS`
  (default 300s). Sync the host clock.

### "Why are some calls tracked and others aren't?"

`@protect` only fires on the functions it's wrapped around. Plain
LLM calls (no `@protect`, no auto-instrumented framework) are
**invisible** to NullRun. If you use a framework that the SDK
auto-instruments (see [How-to → Auto-instrumented frameworks](how-to/auto-instrumented-frameworks.md)),
you do not need `@protect` to get cost tracking.

## See also

- [Errors → exception hierarchy](reference/errors.md)
- [Concepts → Circuit breaker](concepts/circuit-breaker.md)
- [Concepts → Control plane (WebSocket)](concepts/control-plane.md)
- [Reference → HTTP API](reference/http-api.md)
