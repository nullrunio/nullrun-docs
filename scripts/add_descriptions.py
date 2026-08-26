#!/usr/bin/env python3
"""
add_descriptions.py — One-shot script that prepends a YAML front-matter
block with `description:` to every docs page that doesn't already have
one. Used by the SEO/LLM optimisation sprint to give each page a unique
meta description for Google + per-page JSON-LD TechArticle.

Why this exists:
  - Material reads the FIRST PARAGRAPH of a page when no front-matter
    `description` is set. For docs pages that's usually the section
    title (e.g. "Budgets") — not useful as a meta description.
  - The JSON-LD injector in overrides/main.html needs an explicit
    `description` to emit a TechArticle graph node.

Run once, commit, leave as-is. Re-running on an already-described
file is a no-op (checks for existing description key).
"""

import re
import sys
from pathlib import Path

DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"

# Per-file descriptions — concise (≤ 200 chars), action-oriented,
# front-loaded with the noun a searcher would type. Order matches the
# navigation tree in mkdocs.yml.
DESCRIPTIONS = {
    "index.md": "Runtime decision layer for tool-using AI agents. Gates every tool and model call through allow/block/require_approval before execution.",
    "troubleshooting.md": "Common NullRun questions answered: why is my agent blocked, how to debug a gate decision, what to do when a budget doesn't reset.",

    "getting-started/install.md": "Install the NullRun Python SDK with pip, create an API key in the dashboard, and verify the gate is reachable from your environment.",
    "getting-started/quickstart.md": "Decorate your first tool with @protect and ship it through the NullRun gate in under thirty lines of code.",
    "getting-started/tour.md": "Five-minute walkthrough of the NullRun dashboard, policies, and SDK — enough to evaluate the platform end-to-end.",
    "getting-started/configuration.md": "Every NullRun SDK environment variable, transport option, and fail-CLOSED guard documented with safe defaults.",
    "getting-started/onboarding.md": "Wire NullRun into an existing agent in fifteen minutes: install, key, decorate, set a budget, ship.",

    "concepts/circuit-breaker.md": "How NullRun's circuit breaker trips on a budget overrun, recovers after a cooldown, and propagates a kill signal across in-flight calls.",
    "concepts/budgets.md": "Hard and soft budget enforcement, billing-period rollover, and the reserve / consume invariant that protects against implicit re-reservation.",
    "concepts/sensitive-tools.md": "Mark a tool @sensitive to make it fail-CLOSED on transport errors, with no opt-out — the safest class for irreversible actions.",
    "concepts/workflow.md": "Group agent calls into a named workflow, propagate parent_trace_id, and bind cost to a logical unit instead of a single session.",
    "concepts/tracing.md": "OpenTelemetry-style spans for every gate decision, with parent_trace_id propagation so the dashboard renders a true waterfall.",
    "concepts/control-plane.md": "Real-time WebSocket channel for kill, pause, and approval_resolved — the operator's runtime control surface for live agents.",
    "concepts/api-keys.md": "Scopes, two-phase rotation, revocation, and the binding between an API key, its workflow, and its policy cache.",
    "concepts/policies.md": "How BudgetLimit, RateLimit, ToolBlock, and LoopDetection policies are aggregated — most-restrictive-wins semantics across scopes.",
    "concepts/tool-policies.md": "Glob patterns for tool names with a 4 KB cap per pattern, union semantics across applicable scopes, and validation traps to avoid.",
    "concepts/human-approval.md": "Bind approvals to a typed BusinessImpact predicate and a SHA-256 action_digest so the grant refuses if the action payload drifts.",
    "concepts/error-handling.md": "The full NullRun exception hierarchy, kill-signal semantics, and the multi-layer fail-CLOSED contract that protects production traffic.",

    "how-to/langgraph.md": "Auto-instrument a LangGraph agent with @protect, or wrap nodes manually when you need fine-grained control over the gate decision.",
    "how-to/openai-agents.md": "Install the nullrun[agents] extra and gate every tool call from an OpenAI Agents SDK workflow.",
    "how-to/crewai.md": "Wrap CrewAI tools and tasks with @protect so the NullRun gate evaluates every crew action before it executes.",
    "how-to/fastapi.md": "Bind a FastAPI request to a NullRun workflow, propagate trace context, and map gate errors to the right HTTP status code.",
    "how-to/llm-frameworks.md": "Coverage matrix for OpenAI, Anthropic, Mistral, Gemini, Cohere, Bedrock, LangChain, LlamaIndex, CrewAI, AutoGen, and the raw openai SDK.",
    "how-to/cost-cap.md": "Set a per-workflow hard cost cap with alert thresholds, and use Soft mode with an active chain to allow a controlled overdraft.",
    "how-to/multi-agent.md": "Run multiple agents in one workflow, propagate parent_trace_id, and aggregate cost across the team.",
    "how-to/multi-agent-orchestration.md": "Orchestrate sub-agents with shared kill semantics: a top-level trip propagates to every child through the control plane.",
    "how-to/streaming.md": "Use @protect on a stream iterator so the gate's Cancel decision can stop a live response the moment an overrun is detected.",
    "how-to/custom-tracking.md": "Manually report cost and events with track_llm, track_tool, and track_event when auto-instrumentation doesn't fit your runtime.",
    "how-to/ci-cd.md": "Fail-CLOSED gate integration in CI, with smoke-test scripts that verify the gate is reachable before a deploy.",

    "reference/sdk-api.md": "Reference for every NullRun SDK symbol: init, @protect, @sensitive, workflow, chain, exceptions, manual tracking, and transport hooks.",
    "reference/http-api.md": "Every NullRun HTTP endpoint: /api/v1/gate, /api/v1/track, /api/v1/capabilities, /api/v1/heartbeat, and the control-plane WebSocket protocol.",
    "reference/errors.md": "Full NullRun error-code reference: NR-B004 budget blocks, NR-T001 transport errors, NR-R001 refusals, and decision vs infrastructure classes.",
    "reference/llm-tool-catalog.md": "Per-model input and output pricing for every LLM NullRun understands, with capability flags for streaming, tools, and structured output.",

    "compliance/index.md": "NullRun's compliance posture: geo-block at the network edge, sanctions screening at signup, and what to expect when rules degrade.",
    "compliance/geo-restrictions.md": "IP-level blocklists for sanctioned jurisdictions, with the runtime status codes a client sees when a request is geo-blocked.",
    "compliance/sanctions-screening.md": "OFAC SDN screening on signup, the degraded-fallback semantics when the screening service is unavailable, and the audit trail.",
}

FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def has_description(text: str) -> bool:
    m = FRONT_MATTER_RE.match(text)
    if not m:
        return False
    return bool(re.search(r"^description\s*:", m.group(1), re.MULTILINE))


def title_from_filename(path: Path) -> str:
    """Derive a Title-Cased page name from the file stem (e.g.
    'how-to/langgraph.md' → 'Langgraph'). Used when we need to set
    an explicit `title:` so JSON-LD gets a stable headline even
    when the markdown H1 is decorative.
    """
    stem = path.stem.replace("-", " ").replace("_", " ")
    return " ".join(w.capitalize() for w in stem.split())


def inject(path: Path, desc: str) -> bool:
    text = path.read_text(encoding="utf-8")
    if has_description(text):
        return False

    # If there's NO front-matter, prepend one. If there IS one
    # but it lacks description, append a description line.
    m = FRONT_MATTER_RE.match(text)
    if m is None:
        # No front-matter at all — derive title from filename.
        title = title_from_filename(path)
        block = f"---\ntitle: {title}\ndescription: {desc}\n---\n\n"
        path.write_text(block + text, encoding="utf-8")
    else:
        # Front-matter exists, just add description (and title if missing).
        fm = m.group(1)
        additions = []
        if not re.search(r"^title\s*:", fm, re.MULTILINE):
            additions.append(f"title: {title_from_filename(path)}")
        additions.append(f"description: {desc}")
        new_fm = fm.rstrip("\n") + "\n" + "\n".join(additions) + "\n"
        path.write_text(new_fm + text[m.end():], encoding="utf-8")
    return True


def main() -> int:
    changed = 0
    skipped = 0
    missing = []
    for relpath, desc in DESCRIPTIONS.items():
        path = DOCS_DIR / relpath
        if not path.exists():
            missing.append(relpath)
            continue
        if inject(path, desc):
            changed += 1
            print(f"  + {relpath}")
        else:
            skipped += 1
            print(f"  · {relpath} (already has description)")

    print(f"\nChanged: {changed}    Skipped: {skipped}")
    if missing:
        print("Missing files (DESCRIPTIONS dict references non-existent paths):")
        for m in missing:
            print(f"  ! {m}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())