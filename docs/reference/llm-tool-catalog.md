# Tool catalog

A reference list of the tool names LLM agents commonly expose, tagged
with a default risk rating you can use as a starting point when you
register `@sensitive` patterns.

The catalog covers three sources that NullRun sees in production:

- **LangChain built-in toolkits** (`langchain-community` — search, SQL,
  Gmail, Slack, GitHub, file system, vector stores, code interpreters)
- **Anthropic / OpenAI hosted tools** (OpenAI code interpreter, e2b
  sandbox, Riza JS exec)
- **MCP servers** (official + community — filesystem, git, github,
  postgres, sqlite, redis, puppeteer, memory, time)

Names are normalised to `snake_case` — that's the convention
LangChain's docs recommend and every provider we tested parses.

Risk rating:

| Rating | Meaning |
| --- | --- |
| `low` | Read-only or reversible. Safe to call without a policy decision. |
| `medium` | Mutates external state but the change is reversible (issue created, draft email, S3 put). |
| `high` | **Side effects you can't easily undo** — files written or deleted, money moved, messages sent, code executed, infra changed. Mark `@sensitive` and route through a human approval gate. |

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

Any tool that evaluates arbitrary code is `high` by definition —
the blast radius is the entire host or sandbox the agent reaches.

`python_repl`, `python_repl_ast`, `execute_python`,
`code_interpreter` (OpenAI built-in), `e2b_code_interpreter`,
`execute_javascript` (Riza), `execute_code`, `run_command`,
`run_bash_command`, `terminal`, `bash`, `shell`, `repl` — all
**`high`**. Register a blanket pattern (see the starter list below)
rather than enumerating them.

## Databases

| Tool | Risk |
| --- | --- |
| `sql_db_schema`, `sql_db_query_checker`, `read_query` (sqlite) | low |
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
**`high`**. Reads only (`get_balance_sheet`, `get_income_statement`,
`get_cash_flow`) drop to `low`.

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

!!! note
    `puppeteer_evaluate` runs JS in the browser page context — treat
    it as `high` (cross-origin requests, DOM injection, credential
    theft). `browser_navigate` and `browser_click` are `medium`
    because they take actions on whatever URL the agent picks.

## Recommended `@sensitive` starter list

Use this as a starting point, then narrow or widen based on what
your agent actually does. Register on SDK init:

```python title="sensitive_patterns.py"
from nullrun import init

init(
    api_key="nr_live_...",
    sensitive_tool_patterns=[
        # Finance
        "stripe.*", "charge", "send_payment", "create_invoice", "refund",
        # Email & messaging (anything that "sends")
        "send_email", "send_gmail", "send_message", "send_sms",
        "slack_send.*", "office365_send.*",
        # Destructive file ops
        "delete_file", "file_delete", "write_file", "file_write",
        # Destructive DB ops
        "execute_sql", "run_sql", "db_write", "db_delete",
        "write_query", "create_table",
        # Destructive cloud / infra
        "s3_delete.*", "ec2_terminate.*", "ec2_stop.*",
        "lambda_invoke", "kubernetes_delete", "kubernetes_apply",
        # Any code execution
        "python_repl.*", "bash", "shell", "terminal",
        "execute_.*", "run_command", "run_bash_command",
        # Git / GitHub writes
        "git_commit", "github_merge.*", "github_push.*", "github_delete.*",
        # Memory / vector destructive
        "memory_delete", "vector_store_delete", "delete_entities",
    ],
)
```

Patterns are glob-matched against the tool name the agent requested,
case-insensitively — `"Stripe.Charge"` will match `"stripe.*"`.

## See also

- [Sensitive tools](../concepts/sensitive-tools.md) — the fail-CLOSED
  enforcement policy behind `@sensitive`
- [Tool policies](../concepts/tool-policies.md) — glob patterns,
  per-tool block / allow rules
- [SDK API](sdk-api.md) — `runtime.add_sensitive_tool(...)` etc.
