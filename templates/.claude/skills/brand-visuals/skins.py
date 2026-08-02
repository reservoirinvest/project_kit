"""Generator for brand.css — the workspace dashboard theme registry.

    python skins.py            # rewrites brand.css beside this file

It writes the file itself rather than printing to stdout: on Windows a
`> brand.css` redirect encodes in the console codepage and silently turns every
em dash in the comments into a replacement character.

`brand.css` is a committed static file; this script is how it is REGENERATED,
not something any app runs. Adding a skin means adding one row to `SKINS` and
re-running, never hand-editing the CSS.

Why generate at all
-------------------
Three properties are impossible to hold by hand and free to hold here:

1. The two dark blocks (`[data-theme="dark"]` and the `prefers-color-scheme`
   fallback) are emitted from one source, so they cannot drift. In the old seed
   they were two hand-maintained copies of ~20 values.
2. Every skin declares every primitive. A missing one would silently inherit
   navy and nobody would notice until a screenshot looked wrong.
3. Contrast is tuned by construction (see `tune`), not by eyeball. These are
   financial dashboards read for hours.

Navy is the reference — the original RKV seed, unchanged. Every other skin is
navy hue-rotated at held lightness, so each inherits the seed's proven tonal
structure. Status hues and gold are literal and IDENTICAL in every skin: a
warning must look the same in every dashboard. Only their backgrounds move,
blended toward the skin's canvas so a pill sits on it.

The authority on whether the output is acceptable is `tests/test_brand_css.py`,
which re-parses the emitted CSS. It deliberately does not import this file — a
generator that graded its own homework would pass whatever it produced.
"""

from __future__ import annotations

import colorsys

# --- colour helpers ---------------------------------------------------------


def hex2rgb(h: str) -> tuple[float, float, float]:
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))


def rgb2hex(rgb) -> str:
    return "#" + "".join(f"{round(max(0.0, min(1.0, c)) * 255):02x}" for c in rgb)


def rotate(h: str, hue_deg: float, sat_mult: float = 1.0, sat_floor: float = 0.0) -> str:
    """Re-hue a colour, holding its lightness."""
    _, li, sa = colorsys.rgb_to_hls(*hex2rgb(h))
    sa = max(sa * sat_mult, sat_floor) if sa > 0.004 else sa * sat_mult
    return rgb2hex(colorsys.hls_to_rgb(hue_deg / 360, li, min(sa, 1.0)))


def shift_l(h: str, delta: float) -> str:
    hu, li, sa = colorsys.rgb_to_hls(*hex2rgb(h))
    return rgb2hex(colorsys.hls_to_rgb(hu, max(0.0, min(1.0, li + delta)), sa))


def blend(a: str, b: str, t: float) -> str:
    return rgb2hex(tuple(x + (y - x) * t for x, y in zip(hex2rgb(a), hex2rgb(b))))


def luminance(h: str) -> float:
    def lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (lin(c) for c in hex2rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(fg: str, bg: str) -> float:
    lo, hi = sorted((luminance(fg), luminance(bg)))
    return (hi + 0.05) / (lo + 0.05)


def tune(colour: str, bgs: list[str], need: float, direction: int) -> str:
    """Walk lightness in `direction` until `colour` clears `need` on every bg.

    The walk happens in float HLS and quantizes to 8-bit only at the end.
    Stepping via hex round-trips instead lets rounding error accumulate: an
    earlier version drifted navy's #a9b5c4 border 19 degrees of hue into teal
    over 200 steps, silently breaking the very skin identity this file exists
    to establish.
    """
    hu, li, sa = colorsys.rgb_to_hls(*hex2rgb(colour))
    out = rgb2hex(colorsys.hls_to_rgb(hu, li, sa))
    for _ in range(400):
        if all(contrast(out, b) >= need for b in bgs):
            return out
        li += direction * 0.0025
        if not 0.0 <= li <= 1.0:  # hit pure black/white and still short
            break
        out = rgb2hex(colorsys.hls_to_rgb(hu, li, sa))
    return out


# --- the navy reference (the original RKV seed, verbatim) -------------------

NAVY_LIGHT = {
    "canvas": "#f8f9fa",
    "raised": "#eef1f5",
    "surface": "#ffffff",
    "surface-hover": "#eef1f5",
    "hero": "#0e294e",
    "text": "#0a192f",
    "text-secondary": "#2a3a52",
    "text-muted": "#5a6b82",
    "inverse": "#ffffff",
    "border": "#d3dae3",
    "border-strong": "#a9b5c4",
    "divider": "#e2e7ee",
    "accent": "#1e56a0",
    "accent-text": "#1e56a0",
    "accent-soft": "#e7eef7",
}
NAVY_DARK = {
    "canvas": "#07162c",
    "raised": "#0c1f3c",
    "surface": "#0e294e",
    "surface-hover": "#143560",
    "hero": "#0a1f3c",
    "text": "#eaf1fb",
    "text-secondary": "#c2d0e4",
    "text-muted": "#8fa2bd",
    "inverse": "#07162c",
    "border": "#1d3a63",
    "border-strong": "#2f5288",
    "divider": "#17335c",
    "accent": "#3a72c0",
    "accent-text": "#7ba6dc",
    "accent-soft": "#10294a",
}
# ibf's hand-tuned amethyst dark chrome (2026-08-02) is the starting point for
# that skin rather than a rotation of navy, so ibf moves only where contrast
# tuning forces it.
AMETHYST_DARK = {
    "canvas": "#150b26",
    "raised": "#1d1033",
    "surface": "#271545",
    "surface-hover": "#331c59",
    "hero": "#180d2b",
    "text": "#f0eafb",
    "text-secondary": "#d3c8e6",
    "text-muted": "#a394bd",
    "inverse": "#150b26",
    "border": "#3a2560",
    "border-strong": "#55397f",
    "divider": "#2e1c4f",
    "accent": "#8b6ad4",
    "accent-text": "#c3aef0",
    "accent-soft": "#241640",
}

FIXED_LIGHT = {
    "gold": "#d4af37",
    "gold-text": "#000000",
    "success": "#0a7a4f",
    "warning": "#8a6100",
    "danger": "#b42318",
}
FIXED_DARK = dict(FIXED_LIGHT, success="#35b779", warning="#e0b64e", danger="#f06a6a")
BASE_BG_LIGHT = {"success-bg": "#e6f4ee", "warning-bg": "#fbf1d8", "danger-bg": "#fcebe9"}
BASE_BG_DARK = {"success-bg": "#0c2b20", "warning-bg": "#2f2710", "danger-bg": "#331717"}

# name -> (hue, chrome saturation multiplier, light-mode tint floor)
#
# Cool hues only. Green, amber and red are the STATUS palette; a skin in those
# families competes with status meaning, so none is offered. teal is registered
# but reserved: it is Zuellig's livery family (zp_scm, #005d62 = 183 degrees),
# kept here so nothing else claims it.
SKINS = {
    "navy": (215, 1.00, 0.00),
    "indigo": (240, 1.00, 0.10),
    "amethyst": (268, 0.85, 0.10),
    "teal": (185, 1.00, 0.10),
    "slate": (220, 0.28, 0.05),
}
SEAT = {"light": 0.16, "dark": 0.22}  # how far a status bg is dragged to canvas

ORDER = [
    "canvas", "raised", "surface", "surface-hover", "hero", "on-hero", "on-hero-muted",
    "text", "text-secondary", "text-muted", "inverse",
    "border", "border-strong", "divider",
    "accent", "accent-hover", "accent-active", "accent-text", "accent-soft", "on-accent",
    "gold", "gold-text",
    "success", "success-bg", "warning", "warning-bg", "danger", "danger-bg",
]  # fmt: skip


def build(skin: str) -> dict[str, dict[str, str]]:
    hue, sat, floor = SKINS[skin]
    out = {}
    for theme, ref, fixed, bgs in (
        ("light", NAVY_LIGHT, FIXED_LIGHT, BASE_BG_LIGHT),
        ("dark", NAVY_DARK, FIXED_DARK, BASE_BG_DARK),
    ):
        if skin == "amethyst" and theme == "dark":
            c = dict(AMETHYST_DARK)
        elif skin == "navy":
            c = dict(ref)
        else:
            # The tint floor only lifts light mode's near-neutral greys; dark
            # chrome is already saturated enough to read as the skin's hue.
            c = {k: rotate(v, hue, sat, floor if theme == "light" else 0.0) for k, v in ref.items()}

        c.update(fixed)
        c.update({k: blend(v, c["canvas"], SEAT[theme]) for k, v in bgs.items()})

        # --- contrast tuning ------------------------------------------------
        # Text renders on canvas, surface AND raised; take the worst of the three.
        dirn = -1 if theme == "light" else 1  # darken in light, lighten in dark
        fields = [c["canvas"], c["surface"], c["raised"]]
        c["text"] = tune(c["text"], fields, 7.0, dirn)
        c["text-secondary"] = tune(c["text-secondary"], fields, 4.5, dirn)
        c["text-muted"] = tune(c["text-muted"], fields, 4.5, dirn)
        c["accent-text"] = tune(c["accent-text"], fields, 4.5, dirn)
        # A boundary is a UI component under WCAG 1.4.11 -> 3:1, not 4.5. The
        # original seed shipped 1.97:1 here, which is why inputs and card edges
        # were hard to place on a bright screen.
        c["border-strong"] = tune(c["border-strong"], fields, 3.0, dirn)

        # Hover/active track the accent rather than drifting independently:
        # light darkens on hover, dark lightens (the seed's convention).
        d_hover, d_active = (-0.05, -0.10) if theme == "light" else (0.06, -0.05)

        # d_hover/d_active bound as defaults: they are loop variables, and a
        # closure over them would silently follow the NEXT theme's offsets if
        # this helper were ever called outside the iteration that made it.
        def trio(base: str, dh: float = d_hover, da: float = d_active) -> list[str]:
            return [base, shift_l(base, dh), shift_l(base, da)]

        def worst(fg: str, base: str) -> float:
            return min(contrast(fg, x) for x in trio(base))

        # A filled button's foreground is whichever of white / the canvas reads
        # better on the accent — NOT white by decree. Decreeing white would force
        # every bright dark-mode accent to darken until white cleared AA, which
        # would have dragged ibf's amethyst #8b6ad4 down for no reason beyond the
        # tuner's own assumption. Only if neither foreground works does the accent
        # itself move, and then the whole trio moves with it (hover is where a
        # button spends its most-looked-at moments).
        c["on-accent"] = max(("#ffffff", c["canvas"]), key=lambda fg: worst(fg, c["accent"]))
        if worst(c["on-accent"], c["accent"]) < 4.5:
            hu, li, sa = colorsys.rgb_to_hls(*hex2rgb(c["accent"]))
            step = -0.0025 if c["on-accent"] == "#ffffff" else 0.0025
            for _ in range(400):
                cand = rgb2hex(colorsys.hls_to_rgb(hu, li, sa))
                if worst(c["on-accent"], cand) >= 4.5:
                    break
                li += step
                if not 0.0 <= li <= 1.0:
                    break
            c["accent"] = cand
        c["accent-hover"], c["accent-active"] = trio(c["accent"])[1:]

        # The hero bar's own foreground. In light mode the hero is a dark slab,
        # so white sits on it; in dark mode the hero is DARKER than the canvas,
        # so it is not an inverted surface and body text belongs on it. Using
        # --text-inverse for both (as the old seed forced) put #07162c on #0a1f3c
        # — 1.10:1, an invisible header that ibf patched per-project and kite
        # never did.
        c["on-hero"] = c["inverse"] if theme == "light" else c["text"]
        # Secondary text on the hero (an app subtitle, a breadcrumb). It needs
        # its own token because --text-muted is tuned against the canvas, and
        # the hero is a dark slab in BOTH themes: ibf's header subtitle sat at
        # 2.72:1 in light mode using --text-muted. The hero is always the darker
        # surface, so this always brightens toward --on-hero.
        c["on-hero-muted"] = tune(blend(c["on-hero"], c["hero"], 0.38), [c["hero"]], 4.5, 1)
        out[theme] = c
    return out


# --- emit -------------------------------------------------------------------

HEADER = '''/*
 * RKV Strategic Advisory brand — MASTER SEED + DASHBOARD THEME REGISTRY.
 *
 * GENERATED by skins.py in this folder. Do not hand-edit: run
 *     python skins.py
 * Copy the result verbatim into a project. You should never need to edit it
 * there — a project picks its look with ONE attribute:
 *
 *     <html lang="en" data-skin="amethyst">
 *
 * Registry (cool hues only — green/amber/red belong to the status palette and
 * a skin in those families competes with status meaning):
 *
 *     navy      215   default, on :root — no data-skin needed
 *     indigo    240   kite      (8120)
 *     amethyst  268   ibf       (8020) — the app that can place live trades
 *     teal      185   RESERVED for Zuellig livery (zp_scm)
 *     slate     220   mktdb     (8000) — near-neutral
 *
 * Three layers, and the boundary between them is the whole point:
 *   1. primitives  — the ONLY place a colour literal may appear
 *   2/3. semantic  — names shared across every project; values are var() only
 *   4. base        — element defaults
 *
 * The semantic variable NAMES are the contract between projects. Skinning
 * changes primitives, never those names. Sharp geometry (--radius: 0), no
 * gradients, no shadows.
 *
 * Theme: automatic via prefers-color-scheme; manual override with
 * <html data-theme="light"> / <html data-theme="dark">. data-skin and
 * data-theme are independent — a skin defines both of its themes.
 *
 * Every skin is tuned to WCAG AA (AAA for body text) in both themes and
 * verified by tests/test_brand_css.py.
 */

/* 1a. Primitives — skin-independent ----------------------------------------- */
:root {
  --font-heading:
    "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, "Helvetica Neue", sans-serif;
  --font-body:
    -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
  --font-mono: "Cascadia Code", "SF Mono", "Consolas", "Liberation Mono", monospace;

  --radius: 0; /* sharp geometry — brand rule */

  --space-1: 0.25rem;
  --space-2: 0.5rem;
  --space-3: 0.75rem;
  --space-4: 1rem;
  --space-5: 1.5rem;
  --space-6: 2rem;

  --transition-fast: 120ms ease;
}

/* 1b. Primitives — the skin registry ---------------------------------------- */
/* THE ONLY BLOCK IN THIS FILE THAT MAY CONTAIN A COLOUR LITERAL.
 * A client livery is a new [data-skin="<client>"] block here, nothing else.
 * Every skin declares every member; a missing one silently inherits navy. */
'''

# semantic name -> primitive suffix. One table drives light, dark, and the
# prefers-color-scheme fallback, so the three cannot disagree.
SEMANTIC = [
    (None, "surfaces"),
    ("--bg-primary", "canvas"),
    ("--bg-secondary", "raised"),
    ("--surface", "surface"),
    ("--surface-hover", "surface-hover"),
    (None, "text"),
    ("--text-primary", "text"),
    ("--text-secondary", "text-secondary"),
    ("--text-muted", "text-muted"),
    ("--text-inverse", "inverse"),
    (None, "lines"),
    ("--border-subtle", "border"),
    ("--border-strong", "border-strong"),
    ("--divider", "divider"),
    (None, "accent + brand"),
    ("--accent-primary", "accent"),
    ("--accent-hover", "accent-hover"),
    ("--accent-active", "accent-active"),
    ("--accent-text", "accent-text"),
    ("--accent-soft", "accent-soft"),
    ("--on-accent", "on-accent"),
    ("--brand-hero", "hero"),
    ("--on-hero", "on-hero"),
    ("--on-hero-muted", "on-hero-muted"),
    ("--brand-gold", "gold"),
    ("--brand-gold-text", "gold-text"),
    (None, "status"),
    ("--status-success", "success"),
    ("--status-success-bg", "success-bg"),
    ("--status-warning", "warning"),
    ("--status-warning-bg", "warning-bg"),
    ("--status-danger", "danger"),
    ("--status-danger-bg", "danger-bg"),
    (None, "charts — Plotly cannot read custom properties, so app code resolves"),
    (None, "these via getComputedStyle and re-resolves them on theme change"),
    ("--chart-up", "success"),
    ("--chart-down", "danger"),
    ("--chart-grid", "divider"),
    ("--chart-axis", "text-muted"),
    (None, "focus"),
    ("--focus-ring", "accent-text"),
]

BASE = """
/* 4. Base -------------------------------------------------------------------- */
*,
*::before,
*::after {
  box-sizing: border-box;
}

html {
  background: var(--bg-primary);
  color: var(--text-primary);
  font-family: var(--font-body);
  -webkit-font-smoothing: antialiased;
}

body {
  min-height: 100vh;
  margin: 0;
  background: var(--bg-primary);
  color: var(--text-primary);
  line-height: 1.5;
}

h1, h2, h3, h4, h5, h6 {
  margin-block: 0 0.5em;
  color: var(--text-primary);
  font-family: var(--font-heading);
  font-weight: 600;
  line-height: 1.2;
}

a {
  color: var(--accent-text);
  text-underline-offset: 0.16em;
}

:focus-visible {
  outline: 2px solid var(--focus-ring);
  outline-offset: 2px;
}

button,
input,
select,
textarea {
  transition:
    background-color var(--transition-fast),
    border-color var(--transition-fast),
    color var(--transition-fast);
}

button:disabled,
input:disabled,
select:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}
"""


def semantic_body(theme: str, indent: str) -> str:
    lines = [f"{indent}color-scheme: {theme};", ""]
    for name, suffix in SEMANTIC:
        if name is None:
            lines.append(f"{indent}/* {suffix} */")
        else:
            lines.append(f"{indent}{name}: var(--rk-{theme}-{suffix});")
    return "\n".join(lines)


def emit() -> str:
    out = [HEADER]
    for skin in SKINS:
        p = build(skin)
        out.append(':root,\n[data-skin="navy"] {' if skin == "navy" else f'[data-skin="{skin}"] {{')
        for theme in ("light", "dark"):
            out.append(f"  /* {theme} */")
            for k in ORDER:
                out.append(f"  --rk-{theme}-{k}: {p[theme][k]};")
            if theme == "light":
                out.append("")
        out.append("}\n")

    out.append("/* 2. Light theme ------------------------------------------------------------- */")
    out.append(':root,\n[data-theme="light"] {')
    out.append(semantic_body("light", "  "))
    out.append("}\n")

    out.append("/* 3. Dark theme -------------------------------------------------------------- */")
    out.append('[data-theme="dark"] {')
    out.append(semantic_body("dark", "  "))
    out.append("}\n")
    out.append("/* Same declarations, emitted from the same table — they cannot drift. */")
    out.append("@media (prefers-color-scheme: dark) {")
    out.append("  :root:not([data-theme]) {")
    out.append(semantic_body("dark", "    "))
    out.append("  }")
    out.append("}")
    out.append(BASE)
    return "\n".join(out)


if __name__ == "__main__":
    from pathlib import Path

    target = Path(__file__).with_name("brand.css")
    target.write_text(emit(), encoding="utf-8", newline="\n")
    print(f"wrote {target} ({len(emit().splitlines())} lines, {len(SKINS)} skins)")
