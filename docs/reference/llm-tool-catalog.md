---
title: Llm Tool Catalog
description: Per-model input and output pricing for every LLM NullRun understands, with capability flags for streaming, tools, and structured output.
---

# Tool catalog

A reference list of the tool names LLM agents commonly expose, tagged
with a default risk rating you can use as a starting point when you
configure approval-rule patterns. `@protect` is the canonical entry
point; every protected tool auto-attaches a default
`ToolParamsExtractor` for ToolParameters rules.

The catalog covers three sources that NullRun sees in production:

- **LangChain built-in toolkits** (`langchain-community` — search, SQL,
  Gmail, Slack, GitHub, file system, vector stores, code interpreters)
- **Anthropic / OpenAI hosted tools** (OpenAI code interpreter, e2b
  sandbox, Riza JS exec)
- **MCP servers** (official + community — filesystem, git, github,
  postgres, sqlite, redis, puppeteer, memory, time)

Names are normalised to `snake_case` — that's the convention
LangChain's docs recommend.

Risk rating:

| Rating | Meaning |
| --- | --- |
| `low` | Read-only or reversible. Safe to call without a policy decision. |
| `medium` | Mutates external state but the change is reversible (issue created, draft email, S3 put). |
| `high` | **Side effects you can't easily undo** — files written or deleted, money moved, messages sent, code executed, infra changed. Mark with `@protect` (auto-attaches the default `ToolParamsExtractor` for ToolParameters rules) and route through a human approval gate. |

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

## Recommended ToolBlock starter list

The SDK does **not** ship a built-in sensitive tool list (see
[Sensitive tools](../concepts/sensitive-tools.md) for the rationale).
You express "this tool needs review" with a `ToolBlock` policy on
the server, evaluated by the gate on every `/gate` call. The
recommended starter patterns below map to that policy mechanism.

Create a ToolBlock policy in the dashboard under
**Policies → New policy** (pick **Tool block** as the type). The
dashboard renders the
canonical tool name for every framework integration so you can
match against the right string:

```json title="tool_block_policy.json"
{
  "policies": [
    {
      "name": "Sensitive starter (matches the catalog)",
      "type": "ToolBlock",
      "scope": "Org",
      "config": {
        "tool_pattern": [
          "stripe.*", "charge", "send_payment", "create_invoice", "refund",
          "send_email", "send_gmail", "send_message", "send_sms",
          "slack_send.*", "office365_send.*",
          "delete_file", "file_delete", "write_file", "file_write",
          "execute_sql", "run_sql", "db_write", "db_delete",
          "write_query", "create_table",
          "s3_delete.*", "ec2_terminate.*", "ec2_stop.*",
          "lambda_invoke", "kubernetes_delete", "kubernetes_apply",
          "python_repl.*", "bash", "shell", "terminal",
          "execute_.*", "run_command", "run_bash_command",
          "git_commit", "github_merge.*", "github_push.*", "github_delete.*",
          "memory_delete", "vector_store_delete", "delete_entities"
        ]
      }
    }
  ]
}
```

Patterns are glob-matched against the tool name the agent requested,
case-insensitively — `"Stripe.Charge"` will match `"stripe.*"`.

For finer-grained rules (e.g. "block refunds over $500", "require
approval for sends to non-`@internal` addresses"), use the typed
`BusinessImpact` predicate (`money_amount` or `tool_parameters`) — see
[Human approval → typed predicates](../concepts/human-approval.md#typed-predicates).

## See also

- [Sensitive tools](../concepts/sensitive-tools.md) — the policy-
  driven way to express "this tool needs review" (no built-in SDK
  list, all server-side via ToolBlock)
- [Tool policies](../concepts/tool-policies.md) — glob patterns,
  per-tool block / allow rules
- [Human approval](../concepts/human-approval.md) — typed
  `BusinessImpact` predicates for narrower rules

!!! info "Deep dive"

    The catalog is a docs reference; the enforcement lives in
    `backend/src/proxy/http/gate/orchestrator.rs::check_tool_block`.
    The `glob_match` helper implements the pattern language: `*`
    for wildcards (multi-`*` patterns split on every `*` and
    require each non-empty literal segment to appear in order via
    `glob_match_multi`), `|` for alternation, bare literals match
    exactly (no substring), `?` is treated as literal. Pattern
    validation is in
    `backend/src/proxy/http/tool_canonical.rs::validate_tool_pattern`;
    `MAX_POLICY_PATTERN_BYTES = 4096`. Tool names are
    canonicalised via `classify_tool` (`tool_canonical.rs`) —
    Builtin (lowercase ASCII ≤64 chars), `mcp://{server}/{tool}`
    for MCP, `custom:{name}` for custom; invalid format is
    rejected at gate validation as `VALIDATION_FAILED`.

    `ToolBlock` is always Hard: per CLAUDE.md §8, soft mode does
    not soften tool blocks. `tool_blocked()` in
    `backend/src/proxy/http/gate/internal.rs` is a defensive
    backstop that also runs on `/track`, so an SDK that bypasses
    `/check` (or omits `tools` from `/check`) cannot skip
    tool_pattern enforcement on the wire. The gate fails CLOSED
    on a missing `tools` field: if the per-key policy has
    `tool_patterns` and the SDK omits `tools`, the gate blocks
    with `TB-1` reason code (`orchestrator.rs`); the singular
    `tool` field is also resolved into `effective_tools` so
    legacy SDKs cannot bypass by sending the pre-T4 wire shape.
    All Builtin names are lowercase ASCII — the gate's
    classification is the single source of truth. Glob match is
    case-SENSITIVE on the function level
    (`gate/internal.rs` test `glob_match_case_sensitive`); Builtin
    names are lowercased at classification so
    `Stripe.Charge` → `stripe.charge` before the match — this is
    what the docs mean by "case-insensitively" for the
    operator's experience. Glob match does NOT inspect tool
    arguments — that's sandbox responsibility
    (`tool_canonical.rs`); a pattern like `bash.*` blocks any
    bash call regardless of the shell command.

    SDK 0.18.1+ attaches a default
    `ToolParamsExtractor(include_all=True)` on every
    `@protect`-decorated function so the wire payload carries
    `tool_name + params` without a second decorator. Bare
    `@sensitive` raises `NotImplementedError` since SDK 0.18.2 —
    the factory form `@sensitive(impact=...)` is mandatory. The
    dotted-prefix smart match is `bash.*` matches `bash`,
    `bash.foo`, `bash.foo.bar` — bare `bash` AND dotted
    continuations (`orchestrator.rs`). Templates seed
    `bash.*`, `shell.*`, `code.*` patterns; operators expect
    them to catch the bare name. Multi-`*` drop-patterns:
    `*.drop_*` matches `s3.drop_table`, `db.drop_user`, but NOT
    `s3.execute_drop` — the trailing `_` is load-bearing per
    `glob_match_multi_star_drop_pattern_unanchored_ends` test.
    For command-level rules (e.g. "block refunds over $500"),
    use the typed `tool_parameters` predicate via
    `@sensitive(impact=money_outflow(argument="amount"))` rather
    than glob patterns.

    The catalog covers three sources: LangChain built-in
    toolkits (search/SQL/Gmail/Slack/GitHub), Anthropic/OpenAI
    hosted tools (code interpreter, e2b sandbox, Riza JS exec),
    and MCP servers. The `ToolBlock` policy was chosen over a
    built-in SDK list because policies live on the server and
    can be updated without an SDK rollout; per-tool risk rating
    is a starting point, not a hard rule. The recommended
    starter JSON is opinionated: blanket patterns
    (`python_repl.*`, `bash.*`) instead of enumeration, because
    enumeration of every framework's exec tool regresses when a
    new MCP server ships. The 4KB pattern-length cap
    (`MAX_POLICY_PATTERN_BYTES`) keeps a single operator from
    pasting a 100MB regex blob.

    Glob match is name-only — arguments are NOT inspected. For
    command-level rules you need the typed `tool_parameters`
    predicate (`@sensitive(impact=money_outflow(...))`); glob
    patterns cannot express "this argument only". `**` is
    treated literally per `glob_match_no_double_star_support`
    (`gate/internal.rs`). `?` is literal — regex-style
    single-char wildcards are not supported; an operator who
    writes `ba?h` matches the literal 4-char string, not `bash`
    / `ball`. The catalog is docs-only — drift between this
    catalog and the actual tool names the agent calls is a real
    risk; `classify_tool` in `tool_canonical.rs` is the source
    of truth for canonical form, not the catalog. TB-1
    fail-CLOSED on empty `tools`: SDKs that omit `tools` while
    the per-key policy has patterns are blocked (defensive
    against bypass) — pre-fix behaviour let legacy SDKs slip
    past `tool_pattern` enforcement entirely.
