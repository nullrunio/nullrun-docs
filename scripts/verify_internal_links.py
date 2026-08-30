#!/usr/bin/env python3
"""Verify every internal href in /tmp/links.json resolves.

For relative paths, we walk from the source page directory to the
target file and check existence.

For #anchors, we look up the slugified heading id in the target HTML
and report missing ones.

Outputs broken_links.json.
"""
from __future__ import annotations

import json
import re
import sys
import io
from pathlib import Path
from urllib.parse import unquote, urlparse

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SITE = Path(__file__).resolve().parents[1] / "site"

# mkdocs Material uses python-slugify-ish headings: lowercase, replace
# non-word with '-', strip leading/trailing '-'. Match the same scheme.
def slugify(text: str) -> str:
    s = text.lower()
    # Replace anything non [a-z0-9_ -] with empty
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    # Collapse whitespace to single hyphen
    s = re.sub(r"[-\s]+", "-", s).strip("-")
    return s


HEADING_ID_RE = re.compile(r'<h\d[^>]*\bid="([^"]+)"')
ANY_ID_RE = re.compile(r'\bid="([^"]+)"')


def page_anchor_ids(html_text: str) -> set[str]:
    """All id attributes in the page — covers h2/h3 headings AND
    code-line-anchor spans (`id="__codelineno-N-M"`) that Material's
    pymdownx.highlight emits inside code blocks."""
    return set(ANY_ID_RE.findall(html_text))


def heading_text_by_id(html_text: str) -> dict[str, str]:
    """Return id -> textContent for every <hN id=...>."""
    out: dict[str, str] = {}
    for m in re.finditer(r'<h(\d)[^>]*\bid="([^"]+)"[^>]*>(.*?)</h\1>', html_text, flags=re.DOTALL):
        raw = m.group(3)
        # Strip nested tags
        text = re.sub(r"<[^>]+>", "", raw)
        text = re.sub(r"\s+", " ", text).strip()
        out[m.group(2)] = text
    return out


def verify_internal() -> tuple[list[dict], list[dict]]:
    """Return (broken_files, broken_anchors)."""
    data = json.loads(Path("/tmp/links.json").read_text(encoding="utf-8"))

    # Preload all pages' anchor ids for fast lookup. Use the broad
    # `page_anchor_ids` matcher (any `id="..."` attribute) so we
    # cover <h2/h3> headings AND code-line-anchor spans that
    # Material's pymdownx.highlight emits inside code blocks
    # (`id="__codelineno-N-M"`).
    page_ids_cache: dict[str, set[str]] = {}
    for html_path in SITE.rglob("*.html"):
        rel = html_path.relative_to(SITE).as_posix()
        page_ids_cache[rel] = page_anchor_ids(html_path.read_text(encoding="utf-8"))

    broken_files: list[dict] = []
    broken_anchors: list[dict] = []

    for src_page, href in data["internal"]:
        # Skip external-ish that snuck through (e.g. "//cdn..."), but
        # those should be in external — internal here = pure relative.
        parsed = urlparse(href)
        # Split off fragment
        path_part = parsed.path
        frag = parsed.fragment
        # Resolve relative to src_page's directory (always forward slashes)
        if path_part == "":
            target_rel = src_page
        else:
            src_dir = Path(src_page).parent.as_posix()
            base = src_dir if src_dir != "." else ""
            joined = (Path(base) / path_part) if base else Path(path_part)
            # Purepath normalization collapses ".." without touching fs
            target_rel = joined.as_posix()
            # Strip leading "./"
            target_rel = re.sub(r"^\./", "", target_rel)

        # Final absolute-style normalization so path comparisons in
        # the heading-id cache hit. We resolve via SITE and strip back
        # to a site-relative posix path.
        try:
            target_rel = Path(SITE / target_rel).resolve().relative_to(SITE.resolve()).as_posix()
        except (OSError, ValueError):
            pass

        # Build candidate target paths. mkdocs Material always emits
        # trailing-slash directory links and resolves them to index.html,
        # so the only valid non-trailing-slash form is a file path
        # (e.g. .png, .css). Always prefer index.html for directory-style.
        candidates = []
        if target_rel.endswith("/"):
            candidates.append(target_rel + "index.html")
        elif "." in Path(target_rel).name:
            # Looks like a file (e.g. foo.png, foo.html)
            candidates.append(target_rel)
        else:
            # Bare directory name — must resolve to index.html
            candidates.append(target_rel.rstrip("/") + "/index.html")
        # Last-resort fallback
        candidates.append(target_rel.rstrip("/") + "/index.html")

        resolved = None
        for cand in candidates:
            if (SITE / cand).exists():
                resolved = cand
                break
        if not resolved:
            broken_files.append({"src": src_page, "href": href, "tried": candidates})
            continue

        # Check anchor if present
        if frag:
            ids = page_ids_cache.get(resolved, {})
            if frag not in ids:
                broken_anchors.append({
                    "src": src_page,
                    "href": href,
                    "resolved_page": resolved,
                    "missing_anchor": frag,
                })

    return broken_files, broken_anchors


def verify_anchors() -> list[dict]:
    """Verify same-page anchor links too (pure #fragment hrefs).
    Uses the broad `page_anchor_ids` matcher so code-line anchors
    (`#__codelineno-N-M`) are recognized too."""
    data = json.loads(Path("/tmp/links.json").read_text(encoding="utf-8"))
    broken = []
    for src_page, href in data["anchors"]:
        frag = href.lstrip("#")
        if not frag:
            continue
        html = (SITE / src_page).read_text(encoding="utf-8")
        ids = page_anchor_ids(html)
        if frag not in ids:
            broken.append({"src": src_page, "href": href, "missing_anchor": frag})
    return broken


def main() -> int:
    broken_files, broken_anchors = verify_internal()
    same_page_anchors = verify_anchors()

    print(f"Broken internal files:  {len(broken_files)}")
    for x in broken_files:
        print(f"  {x['src']} -> {x['href']}")
    print(f"\nBroken cross-page anchors: {len(broken_anchors)}")
    for x in broken_anchors:
        print(f"  {x['src']} -> {x['href']} (page={x['resolved_page']}, anchor={x['missing_anchor']})")
    print(f"\nBroken same-page anchors:  {len(same_page_anchors)}")
    for x in same_page_anchors:
        print(f"  {x['src']} -> {x['href']}")

    out = {
        "broken_files": broken_files,
        "broken_cross_page_anchors": broken_anchors,
        "broken_same_page_anchors": same_page_anchors,
    }
    Path("/tmp/broken_links.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("\nWrote /tmp/broken_links.json")
    return 0 if not (broken_files or broken_anchors or same_page_anchors) else 1


if __name__ == "__main__":
    sys.exit(main())
