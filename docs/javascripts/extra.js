// NullRun docs — small JS hooks.
//
// Today:
//   1. Theme picker (Helix-style popup) — overrides/partials/header.html
//      renders a button + dropdown of {auto, light, dark, navy}. The
//      chosen theme is written to localStorage and applied via a
//      `data-md-color-scheme="..."` attribute on the <html> element,
//      which Material's CSS variables already key off.
//
//   2. Sidebar hide toggle — bound to the menu-bar hamburger. Toggles
//      a `nr-sidebar-hidden` body class that hides `.md-sidebar--primary`.
//      State persisted to localStorage so the choice survives reloads.
//
//   3. Sidebar numbered-section caret — a click on a section header
//      toggles its inner list visibility (default Material already does
//      this via `navigation.sections`; we re-bind so the caret on the
//      left flips open/closed visually).
//
// Future candidates (deliberately not implemented yet):
//   - "Copy page as Markdown" button next to the title. Material
//     already exposes `content.code.copy` for code blocks; this
//     would extend that to whole pages.

const NR_THEME_KEY = "nullrun-docs-theme";

/* ── 1. Theme picker ─────────────────────────────────────────────── */
(function initThemePicker() {
    const buttons = document.querySelectorAll(".nr-theme-btn");
    if (!buttons.length) return;

    function applyTheme(theme) {
        const html = document.documentElement;
        html.setAttribute("data-md-color-scheme", theme);

        // Update the <select> Material already renders so its native
        // form handlers stay in sync.
        const nativeSelect = document.querySelector("[data-md-component=\"palette\"] select");
        if (nativeSelect) {
            const opt = Array.from(nativeSelect.options).find(o => o.value === theme);
            if (opt) nativeSelect.value = theme;
        }

        try { localStorage.setItem(NR_THEME_KEY, theme); } catch (e) { /* ignore */ }
    }

    // Restore previously chosen theme on load (overrides system default).
    let saved = null;
    try { saved = localStorage.getItem(NR_THEME_KEY); } catch (e) { /* ignore */ }
    if (saved && ["default", "slate", "navy"].includes(saved)) {
        applyTheme(saved);
    }

    buttons.forEach((btn) => {
        btn.addEventListener("click", (ev) => {
            ev.preventDefault();
            const theme = btn.getAttribute("data-theme");
            if (theme === "auto") {
                // Reset to OS preference.
                try { localStorage.removeItem(NR_THEME_KEY); } catch (e) { /* ignore */ }
                const systemDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
                applyTheme(systemDark ? "slate" : "default");
            } else {
                const scheme = theme === "navy" ? "slate" : theme;
                applyTheme(scheme);
            }
        });
    });
})();

/* ── 2. Sidebar hide toggle ─────────────────────────────────────── */
(function initSidebarHide() {
    const KEY = "nullrun-docs-sidebar";
    const drawerToggle = document.getElementById("__drawer");
    if (!drawerToggle) return;

    function apply(state) {
        if (state === "hidden") {
            document.body.classList.add("nr-sidebar-hidden");
            drawerToggle.checked = false;
        } else {
            document.body.classList.remove("nr-sidebar-hidden");
            drawerToggle.checked = true;
        }
    }

    let saved = null;
    try { saved = localStorage.getItem(KEY); } catch (e) { /* ignore */ }
    if (saved === "hidden" || saved === "visible") apply(saved);

    drawerToggle.addEventListener("change", () => {
        const state = drawerToggle.checked ? "visible" : "hidden";
        apply(state);
        try { localStorage.setItem(KEY, state); } catch (e) { /* ignore */ }
    });
})();

/* ── 3. Section caret toggling ─────────────────────────────────────
   Material's `navigation.sections` already wires up section collapse
   via the chevron on the right. We just add a small visual flip on
   the caret so the user can tell at a glance whether a section is
   open or closed. The `[data-md-toggle]` is the canonical hook. */
(function initSectionCaret() {
    document.querySelectorAll(".md-nav--primary .md-nav__item--section > .md-nav__link").forEach((link) => {
        const parent = link.parentElement;
        if (!parent) return;
        parent.classList.add("nr-collapsible");
    });
})();

console.info("[nullrun-docs] extra.js loaded.");