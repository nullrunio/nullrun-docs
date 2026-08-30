#!/usr/bin/env python3
"""Extract every href= and src= link from the rendered docs site.

Writes a JSON report to /tmp/links.json with:
- internal: list of {page, href} — relative hrefs only
- anchors: list of {page, href} — pure #fragment hrefs
- external: list of {page, href} — http(s)://
- sources: list of {page, src} — every src= attribute
- counts per category
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SITE = Path(__file__).resolve().parents[1] / "site"

HREF_RE = re.compile(r'href="([^"]+)"')
SRC_RE = re.compile(r'src="([^"]+)"')


def main() -> int:
    internal = []
    anchors = []
    external = []
    sources = []

    pages = sorted(SITE.rglob("*.html"))
    print(f"Scanning {len(pages)} HTML pages")

    for page in pages:
        text = page.read_text(encoding="utf-8")
        rel = page.relative_to(SITE).as_posix()
        for href in HREF_RE.findall(text):
            if href.startswith(("http://", "https://", "mailto:", "tel:")):
                external.append((rel, href))
            elif href.startswith("#"):
                anchors.append((rel, href))
            elif href.startswith(("javascript:", "data:")):
                pass
            else:
                internal.append((rel, href))
        for src in SRC_RE.findall(text):
            sources.append((rel, src))

    print(f"  internal hrefs:  {len(internal)}")
    print(f"  anchor hrefs:    {len(anchors)}")
    print(f"  external hrefs:  {len(external)}")
    print(f"  src= attributes: {len(sources)}")

    report = {
        "pages_scanned": len(pages),
        "internal": internal,
        "anchors": anchors,
        "external": external,
        "sources": sources,
    }
    Path("/tmp/links.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Wrote /tmp/links.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
