---
title: Errors
description: Where every NullRun exception points — the landing page the SDK links to, and where to find the full error reference.
maturity: stable
---

# Errors

Every NullRun exception carries a `docs_url`. The SDK sets it to this page,
because one page holds the whole vocabulary and a per-code page for every
code would be a worse place to send a reader.

The reference itself lives in one place:
[Error codes → reference](reference/errors.md).

| You have | Go to |
|---|---|
| An `NR-*` code | [NR-* error code catalog](reference/errors.md#nr-error-code-catalog) |
| A gateway wire code, such as `BUDGET_HARD_BLOCKED` | [Gateway wire error codes](reference/errors.md#gateway-wire-error-codes) |
| A Python exception class | [SDK exception hierarchy](reference/errors.md#sdk-exception-hierarchy) |
| A generic API error with an `error` slug | [Generic API errors](reference/errors.md#generic-api-errors) |
| A failure you need to classify, not just name | [Decision vs. infrastructure](reference/errors.md#decision-vs-infrastructure) |

To branch in your own code, read `exc.error_code`. To show the user a message,
call `nullrun.format_user_message(exc)`. To decide whether to retry, read
`exc.retryable`.

See [Concepts → Error handling](concepts/error-handling.md) for the
exception → hook → message flow, and [SDK API](reference/sdk-api.md) for the
fields each exception carries.
