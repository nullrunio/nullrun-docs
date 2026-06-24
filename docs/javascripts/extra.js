// NullRun docs — small JS hooks (currently a stub for future
// enhancements). Kept loaded by mkdocs.yml so we can ship one-off
// scripts without touching theme templates.
//
// Used today:
//   - nothing. The `<noscript>` console-warning below is just to
//     surface to a curious reader that the file is intentionally
//     loaded and is not a forgotten import.
//
// Future candidates (deliberately not implemented yet):
//   - Light/dark mode persistence beyond Material's localStorage
//     default (already works, so not needed).
//   - "Copy page as Markdown" button next to the title. Material
//     already exposes `content.code.copy` for code blocks; this
//     would extend that to whole pages.
//   - Mermaid theme listener that re-renders diagrams on the
//     Material palette toggle (the bundled mermaid runtime picks
//     up CSS vars automatically, but a custom palette could need
//     a nudge).

document.addEventListener("DOMContentLoaded", () => {
  // No-op for now. See comment above.
});

console.info("[nullrun-docs] extra.js loaded (no-op).");