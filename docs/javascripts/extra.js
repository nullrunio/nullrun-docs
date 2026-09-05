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
//   3. Section numbered-title caret auto-flips on open/closed via the
//      `nr-collapsible` class we add in JS (Material's stock behaviour
//      is unchanged — we just rotate the caret visually).
//
//   4. Search dialog — Material's overlay only closes the dialog on
//      a click over the overlay surface. We extend that to "any click
//      outside `.md-search__inner`" so a click on the page body (or
//      any non-dialog content) also closes the dialog. The menu-bar
//      magnifier trigger is hidden in CSS; search remains openable via
//      the `/` keyboard shortcut.
//
// The menu-bar title h1 is intentionally hidden — the menu-bar is just
// an icon strip; section context lives in the left sidebar. The
// title-sync hook from earlier revisions has been removed (dead code).

const NR_THEME_KEY = "nullrun-docs-theme";

/* ── 1. Theme picker ─────────────────────────────────────────────── */
(function initThemePicker() {
    const buttons = document.querySelectorAll(".nr-theme-btn");
    if (!buttons.length) return;

    // Map user-facing theme names to Material's expected values.
    // Two product themes (cream / machined-black) — navy was retired
    // 2026-08-30 (was a helix-parity hack, not part of the product
    // design system).
    const themeMap = {
        light: { scheme: "default", primary: "black", accent: "grey", bodyClass: "" },
        dark:  { scheme: "slate",   primary: "white", accent: "grey", bodyClass: "" },
    };

    function clearBodyClasses() {
        // No-op today (navy retired); kept for future theme additions.
    }

    function applyTheme(name) {
        const t = themeMap[name];
        if (!t) return;

        // Material reads these from <body>, not <html>.
        clearBodyClasses();
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
        const willHide = !document.body.classList.contains("nr-sidebar-hidden");
        apply(willHide ? "hidden" : "visible");
        try { localStorage.setItem(KEY, willHide ? "hidden" : "visible"); } catch (e) { /* ignore */ }
    });
})();

/* ── 3. Section caret toggling ─────────────────────────────────────
   Material's `navigation.sections` already wires up section collapse
   via the chevron on the right. We add a `nr-collapsible` class so
   the CSS knows these are accordion sections (vs. plain links). */
(function initSectionCaret() {
    document.querySelectorAll(".md-nav--primary .md-nav__item--section").forEach((item) => {
        item.classList.add("nr-collapsible");
    });
})();

/* ── 4. Search dialog — click-outside to close ─────────────────────
   Material's overlay (`.md-search__overlay` is a `<label for="__search">`
   bound to the hidden checkbox) closes the dialog when clicked, but
   only over the overlay area. If the user focuses the search input
   and then clicks somewhere outside BOTH the dialog and the overlay
   (e.g. on the body content), the dialog stays open. User feedback
   2026-09-03: "когда я нажимаю на поле поиска потом клик на страницу
   — ничего не делает, поиск не убирается". Close the dialog on any
   click whose target isn't inside `.md-search__inner` — toggle the
   `__search` checkbox the same way Material's overlay does. We also
   reset focus off the input so the next `/` shortcut reopens cleanly. */
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
        const inner = document.querySelector(".md-search__inner");
        if (inner && inner.contains(ev.target)) return;
        // Click landed outside the dialog body → close.
        close();
    });
})();

/* ── 5. Print page body class ─────────────────────────────────────────
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

console.info("[nullrun-docs] extra.js loaded.");