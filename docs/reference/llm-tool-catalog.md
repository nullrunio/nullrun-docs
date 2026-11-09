---
title: LLM tool catalog
description: A catalogue of the tool names AI agents commonly expose, with a risk rating for each and the ToolBlock patterns that cover them.
maturity: stable
---

# Tool catalog

A reference list of the tool names LLM agents commonly expose, tagged
with a risk rating you can use as a starting point when you configure
`ToolBlock` patterns.

`@protect` is the entry point for every protected tool. The tool name
and the call's argument bag both reach the gateway, so a rule can match
on the name and a typed approval rule can read an argument value.

| Rating | Meaning |
| --- | --- |
| `low` | Read-only or reversible. Safe to call without a policy decision. |
| `medium` | Mutates external state, and the change is reversible — an issue created, a draft email, an object stored. |
| `high` | **Side effects you cannot easily undo** — a file written or deleted, money moved, a message sent, code executed, infrastructure changed. Mark it with `@protect` and route it through an approval rule. |

The rating is a starting point, not an enforced value. The gateway
does not carry a risk table; it matches the names you write into a
policy.

## Search & retrieval

| Tool | Risk |
| --- | --- |
| `tavily_search`, `tavily_search_results_json` | low |
| `duckduckgo_search`, `duckduck_results_json` | low |
| `google_search`, `google_search_results_json` | low |
| `bing_search` | low |
| `brave_search` | low |
| `web_search`, `search_web` | low |
| `fetch`, `fetch_url` | low |
| `requests_get` | low |
| `wikipedia`, `arxiv`, `pubmed_search`, `semantic_scholar` | low |
| `news_search`, `search_news` | low |
| `requests_post`, `requests_put`, `requests_patch` | medium |
| `requests_delete` | high |

## File system

| Tool | Risk |
| --- | --- |
| `read_file`, `file_read` | low |
| `list_directory`, `get_file_info`, `search_files`, `file_search` | low |
| `copy_file`, `create_directory` | medium |
| `write_file`, `file_write`, `create_file`, `edit_file` | high |
| `delete_file`, `file_delete`, `move_file` | high |

## Code execution

Any tool that evaluates arbitrary code is `high` by definition. The
blast radius is the whole host or sandbox the agent reaches.

`python_repl`, `python_repl_ast`, `execute_python`,
`code_interpreter`, `e2b_code_interpreter`, `execute_javascript`,
`execute_code`, `run_command`, `run_bash_command`, `terminal`, `bash`,
`shell`, `repl` — all **`high`**. Cover them with one pattern per
family rather than enumerating every framework's code runner.

## Databases

| Tool | Risk |
| --- | --- |
| `sql_db_schema`, `sql_db_query_checker`, `read_query` | low |
| `list_tables`, `describe_table` | low |
| `sql_db_query`, `query_sql_database`, `db_query` | medium |
| `redis_set` | medium |
| `execute_sql`, `run_sql`, `db_write`, `write_query`, `create_table` | high |
| `db_delete`, `redis_delete` | high |

## Git & GitHub

| Tool | Risk |
| --- | --- |
| `git_status`, `git_diff`, `git_log` | low |
| `github_get_issue`, `github_get_pull_request`, `github_list_repos`, `github_get_file`, `github_search_code` | low |
| `github_create_issue`, `github_update_issue`, `github_close_issue`, `github_create_pull_request`, `github_create_repo`, `github_create_branch`, `git_add`, `git_checkout` | medium |
| `git_commit`, `github_merge_pull_request`, `github_push_files`, `github_delete_repo` | high |

## Email & messaging

| Tool | Risk |
| --- | --- |
| `gmail_get_message`, `gmail_search`, `office365_search_emails`, `slack_get_channel`, `slack_get_messages` | low |
| `gmail_create_draft`, `office365_create_draft` | medium |
| `send_email`, `send_gmail`, `gmail_send_message`, `gmail_delete_message`, `office365_send_email`, `slack_send_message`, `slack_schedule_message`, `send_sms` | high |

## Calendar & tasks

| Tool | Risk |
| --- | --- |
| `office365_search_events`, `get_calendar_events` | low |
| `office365_create_event`, `create_calendar_event`, `create_task`, `complete_task` | medium |
| `delete_calendar_event`, `delete_task` | high |

## Cloud & infrastructure

| Tool | Risk |
| --- | --- |
| `s3_get_object`, `s3_list_objects`, `ec2_describe_instances`, `kubernetes_get` | low |
| `s3_put_object`, `docker_run` | medium |
| `s3_delete_object`, `s3_delete`, `ec2_start_instance`, `ec2_stop_instance`, `ec2_terminate_instance`, `lambda_invoke`, `kubernetes_apply`, `kubernetes_delete`, `docker_stop` | high |

## Finance & payments

`stripe_charge`, `stripe_create_customer`, `stripe_refund`,
`stripe_create_payment`, `create_invoice`, `send_payment` — all
**`high`**. Read-only calls (`get_balance_sheet`,
`get_income_statement`, `get_cash_flow`) drop to `low`.

## Memory & vector stores

| Tool | Risk |
| --- | --- |
| `vector_store_search`, `memory_retrieve`, `search_nodes` | low |
| `vector_store_add`, `memory_store`, `create_entities`, `add_observations` | medium |
| `vector_store_delete`, `memory_delete`, `delete_entities` | high |

## Browser & scraping

| Tool | Risk |
| --- | --- |
| `puppeteer_screenshot`, `browser_screenshot`, `scrape_page`, `extract_content` | low |
| `puppeteer_navigate`, `puppeteer_click`, `puppeteer_fill`, `browser_navigate`, `browser_click` | medium |
| `puppeteer_evaluate` | high |

`puppeteer_evaluate` runs JavaScript in the page, so it can make
cross-origin requests, inject DOM, and read credentials. Treat it as
`high`. `browser_navigate` and `browser_click` are `medium` because
they act on whatever URL the agent picks.

## MCP tools

An MCP tool's name is whatever the server exposes. The SDK sends that
name to the gateway unchanged, so a `ToolBlock` pattern has to spell it
the way the server does. The **MCP servers** view in the control center
lists the servers and the tools each one registers — read the names off
there rather than guessing them from the server's documentation.

## Recommended ToolBlock starter list

The SDK keeps a built-in set of sensitive tool names — `stripe.charge`,
`send_email`, `db.delete` and similar. `runtime.get_sensitive_tools()`
returns that set plus any tool registered with
`runtime.register_sensitive_tools(...)`. The set classifies names. It
blocks nothing on its own. A tool is blocked by a `ToolBlock` policy,
and the gateway evaluates that policy on every gate call.

Create the policy in the control center under **Governance → Policies → New
policy**, and pick **Tool block** as the type. The control center renders
the canonical tool name for every framework integration, so you can
match against the right string.

The same policy as a `POST /api/v1/orgs/{org_id}/policies` body:

```json title="tool_block_policy.json"
{
  "name": "Sensitive starter (matches the catalog)",
  "policy_type": "tool_block",
  "scope": "org",
  "config": {
    "tool_pattern": [
      "stripe*", "charge", "send_payment", "create_invoice", "refund",
      "send_email", "send_gmail", "send_message", "send_sms",
      "slack_send*", "office365_send*",
      "delete_file", "file_delete", "write_file", "file_write",
      "execute_sql", "run_sql", "db_write", "db_delete",
      "write_query", "create_table",
      "s3_delete*", "ec2_terminate*", "ec2_stop*",
      "lambda_invoke", "kubernetes_delete", "kubernetes_apply",
      "python_repl*", "bash", "shell", "terminal",
      "execute_*", "run_command", "run_bash_command",
      "git_commit", "github_merge*", "github_push*", "github_delete*",
      "memory_delete", "vector_store_delete", "delete_entities"
    ]
  }
}
```

`tool_pattern` holds an array of strings. One bare string is rejected
with `422`.

Note the trailing `*` on the family patterns. `stripe*` covers
`stripe_charge`, `stripe_refund` and every other `stripe_…` name.
`stripe.*` does not: it matches the bare name `stripe` and dotted
names like `stripe.charge`, and nothing else.

## Pattern syntax

`*` is the only metacharacter. There is no regex.

| Pattern | Matches | Does not match |
| --- | --- | --- |
| `bash` | `bash` | `bash_foo`, `pybash` |
| `bash*` | `bash`, `bash_foo`, `bash.foo` | `pybash` |
| `*.secret` | `aws.secret`, `db.secret` | `secret` |
| `bash.*` | `bash`, `bash.foo`, `bash.foo.bar` | `bash_foo` |
| `*.drop_*` | `s3.drop_table`, `db.drop_user` | `s3.execute_drop` |

Alternatives share one entry. The pipe character separates them, and
each side is evaluated on its own:

```text
bash|sh|shell
```

That entry matches `bash`, `sh` and `shell`, and nothing else.

| Rule | Behaviour |
| --- | --- |
| No `*` | Exact equality. A bare literal is never a substring match. |
| One `*` | Anchored prefix and/or suffix. `db.drop_*` needs the prefix; `*.secret` needs the suffix. |
| Two or more `*` | Every literal segment must appear in the value, in order. The ends stay anchored when the pattern does not start or end with `*`. |
| `prefix.*` | The bare prefix **and** any dotted continuation. `bash.*` covers `bash`, `bash.foo` and `bash.foo.bar`. It does not cover `bash_foo`. |
| `\|` | Separates alternatives inside one entry. Each alternative is evaluated on its own. |
| `?` | An ordinary character, not a single-character wildcard. |
| `*` alone | Matches every tool name. |
| `**` | Matches nothing. The policy is accepted, but the pattern never matches a tool. |
| Empty | Matches nothing. |

Matching is case-sensitive. A built-in tool name is lowercase ASCII
letters, digits, `_` and `-`, up to 64 bytes, so write the pattern
in the same shape.

## What a pattern cannot do

Matching reads the tool name only. A pattern never inspects the
arguments, so `bash*` blocks every bash call whatever the command
inside it, and no glob can express a condition on one argument.

For a rule that depends on an argument — "block refunds over $500",
"approve only sends to `@internal` addresses" — use the typed
predicates on an approval rule. See
[Human approval → typed predicates](../concepts/human-approval.md#typed-predicates).

## Other limits

| Limit | Value |
| --- | --- |
| Pattern length | 4096 bytes per entry |
| Pattern characters | No control characters. A pattern with a newline is refused when you save the policy. |
| Enforcement | A tool block is always hard. Soft budget mode does not soften it. |

## See also

- [Tool policies](../concepts/tool-policies.md) — how a `ToolBlock` policy is evaluated
- [Sensitive tools](../concepts/sensitive-tools.md) — the policy-driven way to express "this tool needs review"
- [Human approval](../concepts/human-approval.md) — typed predicates for narrower rules
