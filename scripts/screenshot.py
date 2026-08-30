#!/usr/bin/env python3
"""
Capture dashboard screenshots for the docs site.

For each scenario we record two PNGs (`*-light.png` and `*-dark.png`)
of the same dashboard page in the matching `prefers-color-scheme`
mode. Each screenshot has the relevant button / control outlined with
a high-contrast brand-yellow outline so the docs reader can see
exactly which UI element the prose is talking about.

Output: docs/assets/images/screenshots/<scenario>-{light,dark}.png

Usage:
    python scripts/screenshot.py                # all scenarios
    python scripts/screenshot.py --only api     # subset
    python scripts/screenshot.py --full         # full-page mode
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path
from typing import Any, Callable

from playwright.sync_api import sync_playwright, Page, BrowserContext, Locator

# Force UTF-8 on Windows so the print log doesn't choke on ⚙ / � etc.
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "assets" / "images" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)

BASE = "https://nullrun.io/"
EMAIL = "scalejohn@test.com"
PASSWORD = "N8z7gAhc8Dpf3aw"

VIEWPORT = {"width": 1440, "height": 900}

# Highlight CSS — injected into the dashboard after the page renders.
# Brand yellow (#E6AF1E) outline + soft glow + a small "callout" tag
# pinned to the corner of the element.
HIGHLIGHT_CSS = """
.nr-hl-outline {
    outline: 4px solid #E6AF1E !important;
    outline-offset: 3px !important;
    box-shadow: 0 0 0 6px rgba(230, 175, 30, 0.22) !important;
    position: relative !important;
    z-index: 9999 !important;
}
.nr-hl-tag {
    position: fixed;
    z-index: 99999;
    background: #E6AF1E;
    color: #1A1A1A;
    font: 700 12px/1 ui-monospace, "IBM Plex Mono", monospace;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    padding: 6px 10px;
    border: 2px solid #1A1A1A;
    box-shadow: 4px 4px 0 0 #1A1A1A;
    pointer-events: none;
    white-space: nowrap;
}
"""


# ── login ─────────────────────────────────────────────────────────────

def login(ctx: BrowserContext) -> Page:
    page = ctx.new_page()
    page.goto(BASE, wait_until="domcontentloaded", timeout=60_000)
    if "/control-center" in page.url:
        return page  # session cookie still good
    page.wait_for_timeout(500)
    try:
        page.get_by_role("link", name="Sign in").first.click(timeout=5_000)
    except Exception:
        return page
    page.wait_for_load_state("domcontentloaded", timeout=60_000)
    page.locator("input[type='email']").first.fill(EMAIL)
    page.locator("input[type='password']").first.fill(PASSWORD)
    submit = page.get_by_role("button", name="Sign in").first
    if submit.count() == 0:
        submit = page.locator("button[type='submit']").first
    submit.click()
    page.wait_for_load_state("networkidle", timeout=60_000)
    return page


# ── helpers ───────────────────────────────────────────────────────────

def set_scheme(ctx: BrowserContext, scheme: str) -> Page:
    page = ctx.new_page()
    page.emulate_media(color_scheme=scheme)
    return page


def set_dashboard_theme(page: Page, scheme: str) -> None:
    """The dashboard paints its theme via Tailwind's `dark` class on
    `<html>` (NOT prefers-color-scheme). To capture a light screenshot
    we strip the class; for a dark one we ensure it's there. Doing
    this AFTER navigation means the dashboard's own paint logic
    sees the correct state."""
    if scheme == "dark":
        page.evaluate(
            "() => { document.documentElement.classList.add('dark'); }"
        )
    else:
        page.evaluate(
            "() => { document.documentElement.classList.remove('dark'); }"
        )
    page.wait_for_timeout(150)


def highlight_button(page: Page, locator: Locator, label: str) -> bool:
    """Outline `locator`'s first match + pin a small uppercase tag at
    its top-right with `label` (e.g. "New key"). Returns whether the
    element was found."""
    if locator.count() == 0:
        return False
    page.add_style_tag(content=HIGHLIGHT_CSS)
    # Outline the element AND inject a tag positioned at its top-right.
    page.evaluate(
        """({label}) => {
            const el = document.querySelector('.nr-hl-outline-target');
            if (!el) return false;
            el.classList.add('nr-hl-outline');
            const tag = document.createElement('div');
            tag.className = 'nr-hl-tag';
            tag.textContent = label;
            document.body.appendChild(tag);
            const place = () => {
                const r = el.getBoundingClientRect();
                tag.style.left = (r.right - tag.offsetWidth + 4) + 'px';
                tag.style.top  = (r.top - tag.offsetHeight - 6) + 'px';
            };
            place();
            window.addEventListener('scroll', place, {passive: true});
            window.addEventListener('resize', place);
            window.__nrHlTag = tag;
            return true;
        }""",
        {"label": label},
    )
    return True


def outline_first_match(page: Page, selector: str, label: str) -> bool:
    """Mark the first element matching `selector` as the highlight
    target, then call highlight_button with the body as the locator."""
    page.evaluate(
        """(sel) => {
            document.querySelectorAll('.nr-hl-outline-target')
                .forEach(el => el.classList.remove('nr-hl-outline-target'));
            const el = document.querySelector(sel);
            if (el) el.classList.add('nr-hl-outline-target');
        }""",
        selector,
    )
    return highlight_button(page, page.locator(".nr-hl-outline-target"), label)


def shoot(page: Page, name: str, full: bool = False) -> Path:
    target = OUT / f"{name}.png"
    page.screenshot(path=str(target), full_page=full)
    return target


# ── scenarios ─────────────────────────────────────────────────────────

# (scenario, url, button-name-for-accessible-name, post-action)
# `post_action` runs after the page settles and is responsible for
# highlighting the relevant control before the screenshot.

def _goto(page: Page, path: str) -> None:
    page.goto(BASE.rstrip("/") + path, wait_until="domcontentloaded", timeout=60_000)
    page.wait_for_timeout(800)


def _highlight_via_role(page: Page, role: str, name: str, tag: str) -> bool:
    """Find a control by accessible role+name, mark it as the
    highlight target. Returns whether found."""
    page.evaluate(
        """({role, name}) => {
            document.querySelectorAll('.nr-hl-outline-target')
                .forEach(el => el.classList.remove('nr-hl-outline-target'));
            const els = Array.from(document.querySelectorAll(role));
            for (const el of els) {
                const an = (el.getAttribute('aria-label') || el.innerText || el.textContent || '').trim();
                if (an.toLowerCase() === name.toLowerCase()) {
                    el.classList.add('nr-hl-outline-target');
                    return true;
                }
            }
            return false;
        }""",
        {"role": role, "name": name},
    )
    return highlight_button(page, page.locator(".nr-hl-outline-target"), tag)


def _highlight_text(page: Page, text: str, tag: str) -> bool:
    """Find the first button/link whose accessible text contains
    `text` (case-insensitive substring) and outline it."""
    page.evaluate(
        """(text) => {
            document.querySelectorAll('.nr-hl-outline-target')
                .forEach(el => el.classList.remove('nr-hl-outline-target'));
            const t = text.toLowerCase();
            const els = Array.from(document.querySelectorAll('button, a, [role="button"]'));
            for (const el of els) {
                const an = (el.getAttribute('aria-label') || el.innerText || el.textContent || '').trim().toLowerCase();
                if (an === t || an.includes(t)) {
                    el.classList.add('nr-hl-outline-target');
                    return true;
                }
            }
            return false;
        }""",
        text,
    )
    return highlight_button(page, page.locator(".nr-hl-outline-target"), tag)


def scenario_dashboard_hero(ctx: BrowserContext) -> list[Path]:
    paths = []
    for scheme in ("light", "dark"):
        page = set_scheme(ctx, scheme)
        try:
            _goto(page, "/control-center")
            set_dashboard_theme(page, scheme)
            # Scroll to top to make sure the hero card sits in frame.
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(300)
            paths.append(shoot(page, f"dashboard-hero-{scheme}"))
            print(f"  ✓ dashboard-hero-{scheme}")
        finally:
            page.close()
    return paths


def scenario_workflows_list(ctx: BrowserContext) -> list[Path]:
    paths = []
    for scheme in ("light", "dark"):
        page = set_scheme(ctx, scheme)
        try:
            _goto(page, "/control-center/workflows")
            set_dashboard_theme(page, scheme)
            page.evaluate("window.scrollTo(0, 0)")
            _highlight_text(page, "new workflow", "New workflow")
            page.wait_for_timeout(200)
            paths.append(shoot(page, f"workflows-list-{scheme}"))
            print(f"  ✓ workflows-list-{scheme}")
        finally:
            page.close()
    return paths


def scenario_workflow_new(ctx: BrowserContext) -> list[Path]:
    paths = []
    for scheme in ("light", "dark"):
        page = set_scheme(ctx, scheme)
        try:
            _goto(page, "/control-center/workflows")
            set_dashboard_theme(page, scheme)
            # Click "New workflow" → opens dialog.
            page.evaluate(
                """() => {
                    const els = Array.from(document.querySelectorAll('button, a'));
                    for (const el of els) {
                        const t = (el.innerText || '').trim().toLowerCase();
                        if (t === 'new workflow' || t === '+ new workflow') {
                            el.click();
                            return true;
                        }
                    }
                    return false;
                }"""
            )
            page.wait_for_timeout(800)
            page.wait_for_timeout(200)
            paths.append(shoot(page, f"workflow-new-{scheme}"))
            print(f"  ✓ workflow-new-{scheme}")
        finally:
            page.close()
    return paths


def scenario_workflow_detail(ctx: BrowserContext) -> list[Path]:
    paths = []
    for scheme in ("light", "dark"):
        page = set_scheme(ctx, scheme)
        try:
            # Open the first workflow row (skip the "Open" links that are
            # in the table — click the row label).
            _goto(page, "/control-center/workflows")
            set_dashboard_theme(page, scheme)
            page.wait_for_timeout(400)
            # Pick the first workflow name link on the page.
            page.evaluate(
                """() => {
                    const a = document.querySelector('a[href^="/control-center/workflows/"]');
                    if (a) a.click();
                }"""
            )
            page.wait_for_load_state("domcontentloaded", timeout=30_000)
            page.wait_for_timeout(800)
            paths.append(shoot(page, f"workflow-detail-{scheme}"))
            print(f"  ✓ workflow-detail-{scheme}")
        finally:
            page.close()
    return paths


def scenario_api_keys_list(ctx: BrowserContext) -> list[Path]:
    paths = []
    for scheme in ("light", "dark"):
        page = set_scheme(ctx, scheme)
        try:
            _goto(page, "/control-center/api-keys")
            set_dashboard_theme(page, scheme)
            _highlight_text(page, "new key", "New key")
            page.wait_for_timeout(200)
            paths.append(shoot(page, f"api-keys-list-{scheme}"))
            print(f"  ✓ api-keys-list-{scheme}")
        finally:
            page.close()
    return paths


def scenario_api_key_new(ctx: BrowserContext) -> list[Path]:
    paths = []
    for scheme in ("light", "dark"):
        page = set_scheme(ctx, scheme)
        try:
            _goto(page, "/control-center/api-keys")
            set_dashboard_theme(page, scheme)
            # Click "New key" → opens dialog. Then screenshot.
            clicked = page.evaluate(
                """() => {
                    const els = Array.from(document.querySelectorAll('button, a'));
                    for (const el of els) {
                        const t = (el.innerText || '').trim().toLowerCase();
                        if (t === 'new key' || t === '+ new key') {
                            el.click();
                            return true;
                        }
                    }
                    return false;
                }"""
            )
            page.wait_for_timeout(800)
            page.wait_for_timeout(200)
            paths.append(shoot(page, f"api-key-new-{scheme}"))
            print(f"  ✓ api-key-new-{scheme}  (clicked={clicked})")
        finally:
            page.close()
    return paths


def scenario_policies_list(ctx: BrowserContext) -> list[Path]:
    paths = []
    for scheme in ("light", "dark"):
        page = set_scheme(ctx, scheme)
        try:
            _goto(page, "/control-center/policies")
            set_dashboard_theme(page, scheme)
            _highlight_text(page, "new policy", "New policy")
            page.wait_for_timeout(200)
            paths.append(shoot(page, f"policies-list-{scheme}"))
            print(f"  ✓ policies-list-{scheme}")
        finally:
            page.close()
    return paths


def scenario_approval_rules(ctx: BrowserContext) -> list[Path]:
    paths = []
    for scheme in ("light", "dark"):
        page = set_scheme(ctx, scheme)
        try:
            _goto(page, "/control-center/policies/approval-rules")
            set_dashboard_theme(page, scheme)
            _highlight_text(page, "new rule", "New rule")
            page.wait_for_timeout(200)
            paths.append(shoot(page, f"approval-rules-{scheme}"))
            print(f"  ✓ approval-rules-{scheme}")
        finally:
            page.close()
    return paths


def scenario_approvals(ctx: BrowserContext) -> list[Path]:
    paths = []
    for scheme in ("light", "dark"):
        page = set_scheme(ctx, scheme)
        try:
            _goto(page, "/control-center/approvals")
            set_dashboard_theme(page, scheme)
            page.wait_for_timeout(500)
            paths.append(shoot(page, f"approvals-{scheme}"))
            print(f"  ✓ approvals-{scheme}")
        finally:
            page.close()
    return paths


def scenario_executions(ctx: BrowserContext) -> list[Path]:
    paths = []
    for scheme in ("light", "dark"):
        page = set_scheme(ctx, scheme)
        try:
            _goto(page, "/control-center/executions")
            set_dashboard_theme(page, scheme)
            page.wait_for_timeout(500)
            paths.append(shoot(page, f"executions-{scheme}"))
            print(f"  ✓ executions-{scheme}")
        finally:
            page.close()
    return paths


def scenario_traces(ctx: BrowserContext) -> list[Path]:
    paths = []
    for scheme in ("light", "dark"):
        page = set_scheme(ctx, scheme)
        try:
            _goto(page, "/control-center/traces")
            set_dashboard_theme(page, scheme)
            page.wait_for_timeout(500)
            paths.append(shoot(page, f"traces-{scheme}"))
            print(f"  ✓ traces-{scheme}")
        finally:
            page.close()
    return paths


def scenario_audit_log(ctx: BrowserContext) -> list[Path]:
    paths = []
    for scheme in ("light", "dark"):
        page = set_scheme(ctx, scheme)
        try:
            _goto(page, "/control-center/audit")
            set_dashboard_theme(page, scheme)
            page.wait_for_timeout(500)
            paths.append(shoot(page, f"audit-log-{scheme}"))
            print(f"  ✓ audit-log-{scheme}")
        finally:
            page.close()
    return paths


# ── registry ──────────────────────────────────────────────────────────

SCENARIOS: dict[str, Callable[[BrowserContext], list[Path]]] = {
    "dashboard-hero": scenario_dashboard_hero,
    "workflows-list": scenario_workflows_list,
    "workflow-new": scenario_workflow_new,
    "workflow-detail": scenario_workflow_detail,
    "api-keys-list": scenario_api_keys_list,
    "api-key-new": scenario_api_key_new,
    "policies-list": scenario_policies_list,
    "approval-rules": scenario_approval_rules,
    "approvals": scenario_approvals,
    "executions": scenario_executions,
    "traces": scenario_traces,
    "audit-log": scenario_audit_log,
}


# ── main ──────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", nargs="+", default=None,
                        help="only run scenarios whose key starts with one of these")
    parser.add_argument("--full", action="store_true",
                        help="capture full-page screenshots (default: viewport)")
    args = parser.parse_args()

    chosen = list(SCENARIOS.keys())
    if args.only:
        chosen = [k for k in chosen if any(k.startswith(o) for o in args.only)]

    print(f"Capturing {len(chosen)} scenarios → {OUT}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport=VIEWPORT)
        try:
            login(ctx)
            for key in chosen:
                print(f"\n[{key}]")
                try:
                    SCENARIOS[key](ctx)
                except Exception as e:
                    print(f"  ✗ {key} failed: {e}", file=sys.stderr)
        finally:
            ctx.close()
            browser.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
