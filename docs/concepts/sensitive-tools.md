# Sensitive tools

A **sensitive tool** is one that should never run unattended or without
an explicit policy decision. Examples:

- File system operations (`fs.read`, `fs.write`, `fs.delete`)
- Shell execution (`bash`, `shell.exec`)
- Database writes (`db.write`, `db.migrate`)
- Network egress (`http.fetch` to a non-allowlisted host)
- Code execution (`python.eval`, `node.eval`)

Sensitive tools are listed in the workspace policy. The default list
includes common dangerous operations; you can extend it with
`runtime.add_sensitive_tool(...)` from the SDK.

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
