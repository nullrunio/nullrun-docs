# Sensitive tools

A **sensitive tool** is one that should never run unattended or without
an explicit policy decision. NullRun ships with a built-in list of
high-risk operation patterns:

- Financial operations: `stripe.charge`, `stripe.refund`,
  `stripe.payout`, `payment.process`
- Communication: `send_email`, `send_sms`, `send_slack`, `send_discord`
- Database writes / drops: `db.write`, `db.delete`, `db.drop`,
  `db.truncate`
- External API mutations: `api.post`, `api.put`, `api.delete`
- File / object writes / deletes: `file.write`, `file.delete`,
  `s3.delete`
- Admin: `admin.delete`, `admin.create_user`, `admin.disable_user`

The list is built into the SDK runtime. You can extend it from the
SDK with `runtime.add_sensitive_tool("my.custom_tool")` or
`runtime.register_sensitive_tools([...])` — additions are matched
case-insensitively (a caller passing `"Stripe.Charge"` matches the
built-in `"stripe.charge"`).

## Failure mode

Sensitive tools **fail closed** when the gateway is unreachable. This
is the opposite of the workflow-level breaker (which can fall back to
`PERMISSIVE` or `CACHED`).

Why: if a sensitive operation runs when the policy is unknown, the
blast radius is "agent wrote a file to /etc/passwd" or "agent sent your
data to an attacker". That's worse than a noisy stop.

If you need to override this for a test, set
`NULLRUN_SENSITIVE_FAIL_OPEN=1`. The SDK will emit a `RuntimeWarning`
at import.

## See also

- [Circuit breaker](circuit-breaker.md)
- [Workflow context](workflow.md)
- [Tool catalog](../reference/llm-tool-catalog.md) — common
  tool names LLM agents expose, with a recommended
  `@sensitive` starter list
