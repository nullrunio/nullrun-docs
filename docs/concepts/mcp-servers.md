---
title: MCP servers (Action sources)
maturity: stable
description: What an Action Source is, how the dashboard tells verified servers apart from observed ones, and how to act on drift or stale catalogs.
---

# MCP servers (Action sources)

The **MCP servers** page in the dashboard is the operator's view of
the Model Context Protocol servers your agents actually call. Each
row in the page is one **action source** — the gateway's canonical
name for "one MCP server (or built-in provider) that the SDK has
talked to". The page lives under **Governance → MCP servers** in the
sidebar.

This page covers:

- What an Action Source is and where it comes from.
- How the dashboard splits **verification** (operator-registered,
  probe-driven) from **observation** (SDK-driven, last 30 days).
- What **drift** means, the four states that qualify, and the one
  state that looks like drift but isn't.
- How to **enroll** a discovered source and how to **write an
  approval rule** straight from a catalog action.

For the canonical tool-name format (`mcp://server/tool`) used in
policies and approvals, see [Tool policies](tool-policies.md). For
how tool patterns and approval rules differ, see
[Human approval](human-approval.md).

## What an Action Source is

An Action Source is one entry in the unified table the dashboard
renders for "every MCP-style server we know about". A row appears
either because:

- **You registered it** with a probe URL (`Add action source`),
  and the scheduler polled it and got a tool catalog back.
- **The SDK called it** in the last 30 days. The observation
  helper fires on every `/check` call and adds the source
  automatically.

A row from the first path has a `verification` block; a row from
the second path has only an `observation` block and sits in the
"Discovered but not registered" panel below the main list with an
explicit **Enroll** CTA.

## Page layout

The page header reads **Action sources** and shows the count of
distinct sources in the observation window:

- **N action sources in the last 30 days**, or
- **No MCP action sources yet** when the org is brand new.

The right-side action button is **Add action source** — clicking it
opens a dialog where you paste the MCP probe URL and (optionally)
a label. The scheduler polls new sources every 60 seconds until
the first successful probe lands.

### Metric strip

Four cards above the list give the operator a glance at the
state of the org's tool surface:

| Card | What it counts |
|---|---|
| **Action sources** | Total registered or observed in the window. |
| **Verified** | Sources whose last probe returned a catalog matching observation. Sub-label shows `N unverified — verify now` (a deep link to `?filter=unverified`) or `all sources verified`. |
| **Tool calls** | Total SDK-driven calls across every source in the last 30 days. |
| **Drift** | Real drift only — see below. Sub-label distinguishes `N verification pending — not drift` from `Tools match the upstream catalog`. |

While the page is loading, every card shows `—` rather than `0` —
the dashboard never confuses "I don't know yet" with "the answer is
zero".

### Filter bar

Two controls above the list:

- **Search source or action** — substring match against the
  source URL or any catalog action name.
- **Status chips** — `All` / `Unverified` / `Stale` / `Drift`. Deep
  links via `?filter=<id>` so e.g. the dashboard's "verify now"
  affordance drops the operator on the right view.

## What each row contains

Each row is a hairline-divided tile with three blocks side by side
or stacked:

### Verification block

The left block answers "did the probe succeed?":

- **Verified** — the last probe returned a catalog and it matches
  observation. Sub-line shows `Last verified <timestamp> ·
  re-polls every <interval>`.
- **Stale** — the last probe succeeded but is older than the
  re-poll interval. The next scheduled probe will refresh.
- **Failed** — the last probe errored. The first 200 chars of the
  error body are shown inline (errors are usually JSON Schema
  validation payloads, multi-line HTML, or stack traces); a
  `Show full body` toggle reveals the rest.
- **Never polled** — source was just added; first poll is pending.
- **No probe URL registered** — the source exists only because
  the SDK called it. An inline **Enroll** CTA opens the same
  dialog used by `Add action source`.

### Observation block

The middle block answers "did the SDK actually use this?":

- **N distinct actions called** plus **M total calls in the last
  30 days** when the SDK is active.
- "The SDK hasn't called any action from this source yet" when
  the source is registered but unused.

### Catalog drilldown

A `<details>` toggle below the row, labelled `Actions known (N)`,
expands the catalog. Every row in the catalog shows:

- The action name (`mcp://server/tool`).
- An **Origin** badge: `Probe` (came from a successful probe),
  `Observed` (came from an SDK call), or `Probe + observed` (both).
- A **Create approval rule** deep link to
  `/control-center/policies/approval-rules?prefill_source=…&prefill_action=…`
  so the operator can write a typed-predicate rule for one
  specific action without typing the path.

## Drift — and what isn't drift

The Drift card counts **real drift only**. There are three states
that qualify as drift:

1. **`unannounced` mismatch** — the SDK called actions the last
   probe never listed. Either the upstream catalog moved or
   someone added tools without re-probing. Write approval rules
   for any destructive verb before they are used.
2. **`disappeared` mismatch with prior SDK activity** — the
   probe once succeeded AND the SDK used to call this source, but
   the calls have stopped in the last 30 days. Usually means an
   upstream server upgrade. Review to confirm it isn't the agent
   silently failing over to a different server.
3. **`schema_drift === true`** — an action's input schema (keys
   and types of its argument bag) changed within the window. Pin
   the new schema before allowing the action.

A **`disappeared` source with no prior SDK activity** is NOT
drift — it is verification-pending. The probe never landed and
the SDK never called anything, so we have no baseline to compare
against. The Drift card surfaces these as `N verification pending
— not drift`; the `Unverified` filter is the right view to work
through them.

A row that meets any of the three drift criteria renders a
red-bordered **Drift callout** above the catalog drilldown, with
a per-cause title and one-sentence body explaining what changed
and what to do.

## Discovered but not registered

Below the main list, sources the SDK called but you have not
enrolled show up in a separate panel with the heading **Discovered
but not registered**. Each row has an **Enroll** button that opens
the add-source dialog pre-filled with the URL the SDK last used.
Enrolling moves the source into the main list and starts the
probe scheduler on it.

## Where to read next

- [Tool policies](tool-policies.md) — the `mcp://server/tool`
  canonical-name format and the `ToolBlock` matching rules.
- [Human approval](human-approval.md) — how to write a typed
  approval rule for one action (the deep link in the catalog
  drilldown lands here).
- [Sensitive tools](sensitive-tools.md) — recommended starter
  patterns for destructive actions.
