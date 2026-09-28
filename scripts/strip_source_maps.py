#!/usr/bin/env python3
"""Strip source maps from a built MkDocs site.

`mkdocs-material` compiles its `bundle.*.min.js`, `search.*.min.js`,
and the two stylesheets with esbuild/rollup, which appends both the
map file and a trailing `//# sourceMappingURL=` / `/*# sourceMappingURL=`
comment. MkDocs copies both into `site/` unchanged, so a production
deploy ships ~1.3 MB of source that no reader needs.

The maps are only ever fetched by a developer who has DevTools open,
so leaving them costs nothing in requests but a great deal in bytes:
`bundle.*.min.js.map` alone is ~1 MB, and it is linked from the
one JavaScript file every single page loads.

This removes the `.map` files *and* rewrites the comment that points
at them. Deleting the map without the rewrite is the half-fix — the
comment survives, the browser resolves it, and DevTools shows a 404
for a file the site no longer has.

Usage:

    mkdocs build
    python scripts/strip_source_maps.py            # -> site/
    python scripts/strip_source_maps.py --check    # CI staleness gate

`--check` exits non-zero if anything is left to strip, so the build
pipeline can assert the deployed artifact is map-free without
modifying it.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Trailing sourceMappingURL comment. Both forms are stripped: the `//`
# one from JS, the block-comment one from CSS. Anchored to the end of
# the file with no `re.DOTALL` need, since esbuild always puts the
# comment last.
SOURCEMAP_COMMENT = re.compile(
    rb"(?:\r?\n)?(?://|/\*)#\s*sourceMappingURL=[^\r\n*]*\s*(?:\*/)?\s*\Z"
)

# Extensions worth stripping a comment from. Anything else in site/
# (JSON, HTML) is ours and may legitimately reference a map.
COMMENTED_SUFFIXES = {".js", ".mjs", ".css"}


def iter_candidates(site_dir: Path) -> tuple[list[Path], list[Path]]:
    """Return (map files, assets carrying a sourceMappingURL comment)."""
    maps = sorted(site_dir.rglob("*.map"))
    commented: list[Path] = []
    for path in sorted(site_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in COMMENTED_SUFFIXES:
            try:
                if SOURCEMAP_COMMENT.search(path.read_bytes()):
                    commented.append(path)
            except OSError as exc:  # unreadable file — report, don't crash
                print(f"  ! cannot read {path}: {exc}", file=sys.stderr)
    return maps, commented


def strip(site_dir: Path) -> int:
    maps, commented = iter_candidates(site_dir)
    freed = 0

    for path in maps:
        freed += path.stat().st_size
        path.unlink()
        print(f"  - {path.relative_to(site_dir)}")

    for path in commented:
        data = path.read_bytes()
        stripped = SOURCEMAP_COMMENT.sub(b"", data)
        if stripped != data:
            path.write_bytes(stripped)
            print(f"  ~ {path.relative_to(site_dir)} (comment removed)")

    if not maps and not commented:
        print("  nothing to strip — build is already map-free")
    return freed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--site-dir",
        default="site",
        help="built site directory (default: site)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="report what would be stripped and exit non-zero; do not modify",
    )
    args = parser.parse_args()

    site_dir = Path(args.site_dir)
    if not site_dir.is_dir():
        print(f"error: {site_dir} does not exist — run `mkdocs build` first", file=sys.stderr)
        return 2

    print(f"Scanning {site_dir} for source maps…")
    if args.check:
        maps, commented = iter_candidates(site_dir)
        total = sum(p.stat().st_size for p in maps)
        if maps or commented:
            print(
                f"  {len(maps)} map file(s) ({total:,} bytes) and "
                f"{len(commented)} sourceMappingURL comment(s) still present:"
            )
            for path in maps:
                print(f"    {path.relative_to(site_dir)}")
            for path in commented:
                print(f"    {path.relative_to(site_dir)}")
            print("  run: python scripts/strip_source_maps.py")
            return 1
        print("  clean — no source maps in the build")
        return 0

    freed = strip(site_dir)
    print(f"Done. Reclaimed {freed:,} bytes ({freed / 1024:.0f} KiB).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
