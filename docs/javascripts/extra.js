// NullRun docs — small JS hooks.
//
// Today:
//   1. Theme picker (Helix-style popup) — overrides/partials/header.html
//      renders a button + dropdown of {auto, light, dark, navy}. The
//      chosen theme is applied by setting Material's data-md-color-*
//      attributes on the <body> element (NOT <html> — Material reads
//      from <body>). State is persisted to localStorage under both our
//      key (`nullrun-docs-theme`) and Material's own (`__palette`).
//
//   2. Sidebar hide toggle — bound to the menu-bar hamburger. Toggles
//      a `nr-sidebar-hidden` body class that hides `.md-sidebar--primary`.
//      State persisted to localStorage so the choice survives reloads.
//
//   3. Search dialog — two halves:
//      §3a opens it. The menu-bar search slab is the trigger: clicking
//         anywhere on the field (icon or input) checks `__search`, and
//         `/` or `s` does the same from anywhere on the page. The `/`
//         chip on the right of the slab is a decorative echo of that.
//      §3b closes it. Material's overlay only closes on a click over
//         the overlay surface; we extend that to "any click outside
//         `.md-search__inner`" so a click on the page body (or any
//         non-dialog content) also closes the dialog.
//
//   4. Print page body class — `/print/` gets `nr-print-page` so the
//      CSS can hide the floating TOC and widen the content column.
//
//   5. Mobile sidebar drawer — backdrop, Escape-to-close, and
//      close-on-navigate for viewports ≤76em.
//
//   6. Mermaid diagrams — the `mermaid` superfence (see
//      `pymdownx.superfences.custom_fences` in mkdocs.yml) renders
//      every diagram as `<pre class="nr-mermaid">`. The Mermaid
//      runtime is vendored at `docs/javascripts/mermaid.min.js` and
//      loaded lazily, only on pages that actually contain a diagram,
//      so the other ~40 pages don't pay for it. The loader re-runs
//      on Material's SPA navigation and re-renders on a light/dark
//      switch.
//
//      The `nr-` prefix on the fence class is load-bearing: Material's
//      own bundle watches for `.mermaid`, claims those nodes, and
//      lazily fetches the runtime from unpkg.com — which the site CSP
//      (`script-src 'self'`) blocks, so nothing rendered. Using a
//      distinct class keeps this loader the only renderer. It also
//      lets us render into the light DOM, where the site's print and
//      theme CSS can reach the result — Material renders into a
//      closed shadow root that neither can.
//
//   7. Scrollable-table marker — on a narrow viewport the reference
//      tables are horizontal scrollers (extra.css §16). A scroller
//      with no affordance reads as a table whose right-hand columns
//      are simply cut off, so each wrapper gets a
//      `data-nr-scrollable` attribute whenever it actually has more
//      content than width, and the CSS attaches the fade only then.
//      Recomputed on resize, since the same table is a plain
//      non-scrolling table once the viewport is wide enough.
//
// The menu-bar title h1 is intentionally hidden — the menu-bar is just
// an icon strip; section context lives in the left sidebar.

const NR_THEME_KEY = "nullrun-docs-theme";

/* ── 1. Theme picker ─────────────────────────────────────────────── */
(function initThemePicker() {
    const buttons = document.querySelectorAll(".nr-theme-btn");
    if (!buttons.length) return;

    // Map user-facing theme names to Material's expected values.
    // Two product themes: cream (light) and machined-black (dark).
    const themeMap = {
        light: { scheme: "default", primary: "black", accent: "grey", bodyClass: "" },
        dark:  { scheme: "slate",   primary: "white", accent: "grey", bodyClass: "" },
    };

    function applyTheme(name) {
        const t = themeMap[name];
        if (!t) return;

        // Material reads these from <body>, not <html>.
        document.body.setAttribute("data-md-color-scheme", t.scheme);
        document.body.setAttribute("data-md-color-primary", t.primary);
        document.body.setAttribute("data-md-color-accent", t.accent);
        if (t.bodyClass) document.body.classList.add(t.bodyClass);

        // Persist to localStorage so the choice survives navigation.
        try {
            localStorage.setItem(NR_THEME_KEY, name);
            // Also update Material's __palette so its runtime stays in sync.
            const existing = localStorage.getItem("__palette");
            let parsed = {};
            try { parsed = existing ? JSON.parse(existing) : {}; } catch (e) { parsed = {}; }
            if (!parsed.color) parsed.color = {};
            parsed.color.scheme = t.scheme;
            parsed.color.primary = t.primary;
            parsed.color.accent = t.accent;
            localStorage.setItem("__palette", JSON.stringify(parsed));
        } catch (e) { /* ignore */ }
    }

    function restoreTheme() {
        let saved = null;
        try { saved = localStorage.getItem(NR_THEME_KEY); } catch (e) { /* ignore */ }
        if (saved && themeMap[saved]) {
            applyTheme(saved);
            return saved;
        }
        return null;
    }

    // Restore on first paint (before any flashes of unstyled content).
    restoreTheme();

    buttons.forEach((btn) => {
        btn.addEventListener("click", (ev) => {
            ev.preventDefault();
            const theme = btn.getAttribute("data-theme");
            if (theme === "auto") {
                // Reset to OS preference.
                try { localStorage.removeItem(NR_THEME_KEY); } catch (e) { /* ignore */ }
                const systemDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
                applyTheme(systemDark ? "dark" : "light");
            } else {
                applyTheme(theme);
            }
            // Close the popup after selection.
            const popup = btn.closest(".nr-theme");
            if (popup) popup.blur();
        });
    });
})();

/* ── 2. Sidebar hide toggle ─────────────────────────────────────── */
(function initSidebarHide() {
    const KEY = "nullrun-docs-sidebar";
    const btn = document.querySelector(".nr-sidebar-toggle");
    if (!btn) return;

    function apply(state) {
        if (state === "hidden") {
            document.body.classList.add("nr-sidebar-hidden");
            btn.setAttribute("aria-pressed", "true");
        } else {
            document.body.classList.remove("nr-sidebar-hidden");
            btn.setAttribute("aria-pressed", "false");
        }
    }

    let saved = null;
    try { saved = localStorage.getItem(KEY); } catch (e) { /* ignore */ }
    if (saved === "hidden" || saved === "visible") apply(saved);

    btn.addEventListener("click", () => {
        const isMobile = window.matchMedia("(max-width: 76em)").matches;
        if (isMobile) {
            // Mobile: drive the drawer via `nr-sidebar-open`. The CSS
            // hides the sidebar by default (transform -100%) and only
            // the open class brings it back into view — so toggling
            // `nr-sidebar-hidden` here would actually keep the drawer
            // closed (the global rule at extra.css:306 sets the
            // sidebar to translateX(-100%) when that class is on
            // body). We still flip `nr-sidebar-hidden` in lockstep so
            // a window resize to ≥76em honours the user's intent: if
            // they closed the drawer on mobile, the sidebar stays
            // collapsed on desktop instead of springing back open.
            const willOpen = !document.body.classList.contains("nr-sidebar-open");
            document.body.classList.toggle("nr-sidebar-open", willOpen);
            document.body.classList.toggle("nr-sidebar-hidden", !willOpen);
        } else {
            // Desktop: collapse / expand via the `nr-sidebar-hidden`
            // toggle.
            const willHide = !document.body.classList.contains("nr-sidebar-hidden");
            apply(willHide ? "hidden" : "visible");
        }
        try {
            const stored = isMobile
                ? (document.body.classList.contains("nr-sidebar-open") ? "visible" : "hidden")
                : (document.body.classList.contains("nr-sidebar-hidden") ? "hidden" : "visible");
            localStorage.setItem(KEY, stored);
        } catch (e) { /* ignore */ }
    });
})();

/* ── 3a. Search dialog — open ─────────────────────────────────────────
   The menu-bar carries Material's collapsed search as a visible slab
   (extra.css §4, "SEARCH SLAB"). Material's own trigger is the
   `<label for="__search">` inside the form; the slab's input sits on
   top of it in the visual order and swallowed the click. So we drive
   the checkbox ourselves from the form, which makes the whole slab —
   icon, field, and padding — one hit target, the way MDN, Vercel and
   Stripe all behave.

   The `/` and `s` shortcuts are bound on the capture phase with
   `stopPropagation()`. Material's bundle binds its own document-level
   listener for the same keys, and two listeners toggling the same
   checkbox in the same tick is a guaranteed double-toggle. Capturing
   first and stopping propagation means only ours runs.

   `mousedown` rather than `click` on the form, with `preventDefault`,
   so the browser's own focus handling doesn't fight ours: we open the
   dialog and focus the input in the same turn, and the caret lands
   where the reader expects it. */
(function initSearchTrigger() {
    const checkbox = document.getElementById("__search");
    if (!checkbox) return;
    const form = document.querySelector(".md-search__form");
    if (!form) return;
    const input = form.querySelector(".md-search__input");

    /* Decorative `/` chip on the right of the closed slab. Material's
       `partials/search.html` has no slot for it and we don't override
       that partial (the dialog markup there is load-bearing), so it's
       injected here. The header isn't swapped by `navigation.instant`,
       so this runs once per page load and the chip persists. */
    if (!form.querySelector(".nr-search-hint")) {
        const hint = document.createElement("span");
        hint.className = "nr-search-hint";
        hint.setAttribute("aria-hidden", "true");
        hint.textContent = "/";
        form.appendChild(hint);
    }

    function open() {
        if (checkbox.checked) return;
        checkbox.checked = true;
        checkbox.dispatchEvent(new Event("change"));
        if (input) input.focus();
    }

    form.addEventListener("mousedown", (ev) => {
        // Already open — let the click through so the field can be
        // focused and the caret placed by the user's own click.
        if (checkbox.checked) return;
        ev.preventDefault();
        open();
    });

    document.addEventListener("keydown", (ev) => {
        if (ev.key !== "/" && ev.key !== "s") return;
        if (ev.metaKey || ev.ctrlKey || ev.altKey) return;
        // Never steal a keystroke from a field the reader is typing in.
        const el = document.activeElement;
        if (el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA" ||
                   el.tagName === "SELECT" || el.isContentEditable)) return;
        ev.preventDefault();
        ev.stopPropagation();
        if (checkbox.checked) {
            checkbox.checked = false;
            checkbox.dispatchEvent(new Event("change"));
        } else {
            open();
        }
    }, true);
})();

/* ── 3b. Search dialog — click-outside to close ─────────────────────
   Material's overlay (`.md-search__overlay` is a `<label for="__search">`
   bound to the hidden checkbox) closes the dialog when clicked, but
   only over the overlay area. If the user focuses the search input
   and then clicks somewhere outside BOTH the dialog and the overlay
   (e.g. on the body content), the dialog stays open. Close the dialog on any
   click whose target isn't inside `.md-search__inner` — toggle the
   `__search` checkbox the same way Material's overlay does. We also
   reset focus off the input so the next `/` shortcut reopens cleanly.

   The overlay label is explicitly exempt. A `<label for="__search">`
   toggles its checkbox in the browser's post-click activation step,
   i.e. AFTER this bubbling listener runs — so closing here would
   uncbox the checkbox only for the label to re-check it, and the
   dialog would never dismiss. Material's own overlay handler is the
   right one for that surface. */
(function initSearchClickOutside() {
    const checkbox = document.getElementById("__search");
    if (!checkbox) return;

    function close() {
        if (!checkbox.checked) return;
        checkbox.checked = false;
        // Material listens for `change` on this checkbox to flip its
        // own aria / class state, so dispatching it keeps Material's
        // internal JS in sync (mirrors what the overlay <label> does).
        checkbox.dispatchEvent(new Event("change"));
    }

    document.addEventListener("click", (ev) => {
        if (!checkbox.checked) return;
        if (ev.target.closest && ev.target.closest(".md-search__overlay")) return;
        const inner = document.querySelector(".md-search__inner");
        if (inner && inner.contains(ev.target)) return;
        // Click landed outside the dialog body → close.
        close();
    });
})();

/* ── 4. Print page body class ─────────────────────────────────────────
   `/print/` is a single-page printable edition. We add a body class
   when the URL matches so CSS can:
     - hide the right-side TOC (the page is one long document; a
       floating TOC competes with the on-page TOC anchor list)
     - let the content column use the full width
   The class is applied on first paint AND on Material's SPA
   navigation, since `extra.js` re-runs only on initial load — the
   popstate listener catches subsequent nav-internal navigations. */
(function initPrintPageClass() {
    function apply() {
        const isPrint = window.location.pathname.replace(/\/+$/, "").endsWith("/print");
        document.body.classList.toggle("nr-print-page", isPrint);
    }
    apply();
    window.addEventListener("popstate", apply);
    /* Material's SPA nav uses fetch + pushState; popstate alone misses
       forward navigation. Hook into the click on internal links as a
       cheap approximation that fires before the SPA swap. */
    document.addEventListener("click", (ev) => {
        const a = ev.target.closest("a[href]");
        if (!a) return;
        const url = new URL(a.href, window.location.origin);
        if (url.origin !== window.location.origin) return;
        // Defer until after the SPA swap so the new pathname is set.
        setTimeout(apply, 0);
    });
})();

/* ── 5. Mobile sidebar drawer UX ────────────────────────────────────
   On viewports ≤76em, the sidebar collapses to a drawer that slides
   in from the left when the user taps the hamburger. The matching
   CSS lives in extra.css §16 (backdrop, slide-in animation, body
   scroll lock) — this module owns the runtime:

     - Lazily creates a backdrop <div> on first open and appends to
       <body>. Reused across opens, removed from layout only when the
       drawer closes (pointer-events go to none so it doesn't block
       page clicks while hidden).
     - Closes the drawer on backdrop click.
     - Closes on Escape key (a11y expectation for modal-ish UI).
     - Closes after the user taps any link inside the drawer — defer
       one tick so Material's SPA swap can register the navigation
       before we tear down.
     - Drops the open state if the viewport grows past 76em (e.g.
       device rotation) so the drawer doesn't get stuck in a
       transform limbo when the desktop layout takes over.

   `initSidebarHide` (above) owns the toggle button + localStorage
   persistence; this module only owns the drawer lifecycle that lives
   on top of it. The two cooperate via the `nr-sidebar-open` body
   class — set by the toggle on mobile, observed + reacted to here. */
(function initMobileSidebarUX() {
    const MQ = window.matchMedia("(max-width: 76em)");

    function ensureBackdrop() {
        let el = document.querySelector(".nr-sidebar-backdrop");
        if (!el) {
            el = document.createElement("div");
            el.className = "nr-sidebar-backdrop";
            el.setAttribute("aria-hidden", "true");
            document.body.appendChild(el);
            // Click on backdrop → close drawer (mirrors closing the
            // menu by tapping the hamburger again, but reachable from
            // the dimmed area outside the drawer itself).
            el.addEventListener("click", () => {
                document.body.classList.remove("nr-sidebar-open");
                document.body.classList.add("nr-sidebar-hidden");
                try {
                    localStorage.setItem("nullrun-docs-sidebar", "hidden");
                } catch (e) { /* ignore */ }
            });
        }
        return el;
    }

    // React to body-class changes driven by initSidebarHide. We don't
    // bind to the toggle button directly — that would couple the two
    // modules and break if either changes its handler.
    new MutationObserver(() => {
        const isOpen = document.body.classList.contains("nr-sidebar-open");
        if (isOpen) ensureBackdrop();
    }).observe(document.body, {
        attributes: true,
        attributeFilter: ["class"],
    });

    // Escape closes the drawer (a11y convention for any overlay-like
    // UI; doesn't fire on desktop because nr-sidebar-open is only set
    // on mobile).
    document.addEventListener("keydown", (ev) => {
        if (ev.key !== "Escape") return;
        if (!document.body.classList.contains("nr-sidebar-open")) return;
        document.body.classList.remove("nr-sidebar-open");
        document.body.classList.add("nr-sidebar-hidden");
    });

    // After tapping a link inside the drawer, close it so the user
    // sees the new page without the drawer covering it. Defer one
    // tick so Material's navigation.tracking handler can run first
    // and start the page swap before we tear down.
    document.addEventListener("click", (ev) => {
        if (!document.body.classList.contains("nr-sidebar-open")) return;
        const link = ev.target.closest("a[href]");
        if (!link) return;
        if (!link.closest(".md-sidebar--primary")) return;
        setTimeout(() => {
            document.body.classList.remove("nr-sidebar-open");
            document.body.classList.add("nr-sidebar-hidden");
        }, 0);
    });

    // When the viewport grows past 76em (landscape rotation, window
    // resize on a hybrid device), drop the open state so the sidebar
    // renders inline via the desktop layout instead of staying in the
    // mobile drawer position.
    MQ.addEventListener("change", (e) => {
        if (!e.matches) document.body.classList.remove("nr-sidebar-open");
    });
})();

/* ── 6. Mermaid diagrams ─────────────────────────────────────────────
   `pymdownx.superfences` turns every ```mermaid fence into
   `<pre class="nr-mermaid"><code>…</code></pre>`. Without a runtime
   on the page that renders as a code block, so we load Mermaid on
   demand and call `run()` over those elements.

   Loading is lazy on purpose. The vendored bundle is ~2.5 MB
   (≈800 KB over the wire, then cached by the browser); only four
   pages carry a diagram, so injecting it from every page would tax
   every page. `npm`-installed Material was never an option here —
   the CSP in overrides/main.html is `default-src 'self'` with a
   locked-down `script-src`, and the same-origin vendored copy keeps
   that policy intact.

   Before the first pass we rewrite each node's content from
   `<code>source</code>` to plain `source`. Mermaid reads a node's
   innerHTML, and the `<code>` wrapper that superfences emits makes it
   try to detect the diagram type from the literal string `<code>` —
   which fails with "No diagram type detected". Our snapshot doubles
   as the reset path for a theme switch, since Mermaid replaces the
   content with generated SVG and flags the node `data-processed`.

   `securityLevel: "strict"` keeps label text out of raw HTML, and
   `htmlLabels: false` avoids <foreignObject>, which does not inherit
   our font stack reliably. */
(function initMermaid() {
    // Resolve the docs root from this script's own src so the loader
    // works from any page depth under `use_directory_urls: true`
    // (e.g. /concepts/budgets/ would otherwise resolve `../` to
    // /concepts/ and 404).
    const self = document.currentScript;
    const root = self ? new URL("../", self.src).pathname : "/";

    const SELECTOR = ".nr-mermaid";
    let runtime = null;   // resolved once the script tag has executed
    let themed = "";      // theme the current SVGs were rendered with
    let pending = false;  // collapse overlapping async passes

    function isDark() {
        const attr = document.body.getAttribute("data-md-color-scheme");
        if (attr) return attr === "slate" || attr === "black";
        return window.matchMedia("(prefers-color-scheme: dark)").matches;
    }

    function load() {
        if (runtime) return runtime;
        runtime = new Promise((resolve, reject) => {
            const el = document.createElement("script");
            el.src = root + "javascripts/mermaid.min.js";
            el.onload = () => resolve(window.mermaid);
            el.onerror = () => reject(new Error("mermaid.min.js failed to load"));
            document.head.appendChild(el);
        });
        return runtime;
    }

    async function render() {
        if (pending) return;
        const nodes = Array.from(document.querySelectorAll(SELECTOR));
        if (!nodes.length) { themed = ""; return; }

        const theme = isDark() ? "dark" : "neutral";

        // The theme guard alone is not enough to skip this pass.
        // Clicking a heading permalink changes the hash, and Material's
        // instant navigation responds by replacing the whole content
        // node — so `nodes` are brand-new elements that have never been
        // rendered, sitting at `visibility: hidden` (extra.css) with no
        // `data-nr-mermaid-rendered`. `themed` still equalled the
        // current theme, so the old guard returned early and the
        // diagrams stayed invisible until a full reload.
        //
        // Skip only when the theme is unchanged AND every node on the
        // page has already produced an SVG. A node that has not is
        // either brand new (SPA swap) or was reset for a re-render, and
        // both need this pass to run.
        const allRendered = nodes.every(
            (n) => n.hasAttribute("data-nr-mermaid-rendered") && n.querySelector("svg")
        );
        if (themed === theme && allRendered) return;

        pending = true;
        try {
            const mermaid = await load();
            mermaid.initialize({
                startOnLoad: false,
                securityLevel: "strict",
                theme: theme,
                htmlLabels: false,
                fontFamily: '"IBM Plex Mono", ui-monospace, monospace',
                // Mermaid's default label wrap is ~180px, which is
                // narrower than the 702px frame. With `htmlLabels:
                // false` a long identifier that does not fit gets
                // hard-broken mid-token — "NullRunBlockedException"
                // rendered as "NullRunBlockedExcept ion", and
                // "BUDGET_ORG_CEILING_B_LOCKED" across three lines.
                // Widening the wrap budget lets a whole token sit on
                // one line; the `.nr-mermaid` wrapper is already
                // `overflow-x: auto`, so a genuinely wide diagram
                // scrolls instead of reflowing into nonsense.
                flowchart: { wrappingWidth: 320 },
                // Diagram is laid out at natural size and allowed to
                // scroll horizontally rather than being scaled down
                // to the frame, which is what made the small
                // sequence diagram's labels illegible.
                useMaxWidth: false,
            });

            for (const node of nodes) {
                if (!node.hasAttribute("data-nr-mermaid-src")) {
                    node.setAttribute("data-nr-mermaid-src", node.textContent);
                }
                node.removeAttribute("data-processed");
                node.textContent = node.getAttribute("data-nr-mermaid-src");
            }

            await mermaid.run({ nodes: nodes });
            // Reveal only once every diagram on the page has an SVG —
            // `.nr-mermaid` is `visibility: hidden` until then, so the
            // raw fence source never flashes inside the frame.
            for (const node of nodes) {
                if (node.querySelector("svg")) {
                    node.setAttribute("data-nr-mermaid-rendered", "");
                }
            }
            themed = theme;
        } catch (err) {
            // A malformed diagram shouldn't take the rest of the page
            // with it — leave the fence as readable text instead, and
            // clear `themed` so a later pass can retry.
            themed = "";
            console.warn("[nullrun-docs] mermaid render failed:", err);
        } finally {
            pending = false;
        }
    }

    // Material's SPA nav swaps content in place and does not
    // re-execute this file, so the first paint and every internal
    // navigation both come through here.
    render();
    window.addEventListener("popstate", render);

    // Light/dark switch: re-render the diagrams against the new theme.
    new MutationObserver(render).observe(document.body, {
        attributes: true,
        attributeFilter: ["data-md-color-scheme"],
    });
})();

/* ── 7. Scrollable-table marker ─────────────────────────────────────
   On a narrow viewport the reference tables become horizontal
   scrollers (extra.css §16, "Tables"). A scroller with no affordance
   is indistinguishable from a table whose right-hand columns are
   cropped — which is exactly how it read before the wrapper was
   promoted to the scroll container.

   The fade is a CSS `mask` on the wrapper, gated on this attribute so
   it appears only when there is genuinely something off-screen. A
   mask (rather than a gradient overlay) is what makes that work: an
   overlay element would sit on top of the table and swallow the
   touch-drag that scrolls it.

   The check is `scrollWidth > clientWidth` on the wrapper, recomputed
   on resize — the same table stops being scrollable once the viewport
   is wide enough, and a stale marker would leave a fade hanging off
   the right edge of a table that ends there. Re-runs after Material's
   SPA navigation swaps the content, same as the Mermaid loader. */
(function initScrollableTables() {
    const SELECTOR = ".md-typeset__table";

    function mark() {
        for (const el of document.querySelectorAll(SELECTOR)) {
            if (el.scrollWidth > el.clientWidth + 1) {
                el.setAttribute("data-nr-scrollable", "");
            } else {
                el.removeAttribute("data-nr-scrollable");
            }
        }
    }

    mark();
    window.addEventListener("popstate", mark);

    // Debounced: a drag-resize fires `resize` continuously, and each
    // pass walks every table on the page forcing a layout flush.
    let t = null;
    window.addEventListener("resize", () => {
        clearTimeout(t);
        t = setTimeout(mark, 120);
    });

    // The synchronous `mark()` above measures too early. extra.js is
    // parsed at the end of <body>, before the first layout has been
    // performed and before the webfont faces have swapped in, so every
    // wrapper still reports `scrollWidth === clientWidth` and nothing
    // gets marked. Two deferred passes fix that — one on the next
    // frame (styles applied, layout flushed) and one when the fonts
    // have actually loaded, since the fallback face has different
    // column widths and can flip the answer either way. */
    requestAnimationFrame(mark);
    if (document.fonts && document.fonts.ready) {
        document.fonts.ready.then(mark);
    }
    window.addEventListener("load", mark);
})();

console.info("[nullrun-docs] extra.js loaded.");