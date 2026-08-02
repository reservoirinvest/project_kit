"""The brand rules, enforced.

`brand.css` carries the dashboard theme registry: five named skins, selected
with one `data-skin` attribute. These tests exist because every rule below has
already been broken at least once in this workspace:

- a project accumulated 196 inline hex values while carrying the brand skill
- the seed's two dark blocks were hand-maintained copies, free to drift
- the seed hardcoded its palette in the SEMANTIC layer, which the brand law
  forbids editing, so a dark-mode skin could not be done the sanctioned way
- the seed shipped a 1.10:1 app header in dark mode, which one project patched
  locally and another simply displayed

They deliberately do NOT import `skins.py`, the generator that produces
`brand.css`. A generator that graded its own homework would pass whatever it
produced; these re-parse the committed file as a browser would read it.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

# `#abc` / `#aabbcc` / `#aabbccdd` — but not a CSS id selector or a URL fragment.
HEX_RE = re.compile(r"#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b")
# `var(--token, <anything>)` — a fallback is a second palette that only appears
# when the first one breaks.
VAR_FALLBACK_RE = re.compile(r"var\(\s*--[a-zA-Z0-9-]+\s*,")
COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)

SEMANTIC_RE = re.compile(
    r"^\s*(--(?:bg|surface|text|border|divider|accent|brand|status|focus|on|chart)[a-z-]*):",
    re.M,
)
DECL_RE = re.compile(r"(--[a-z0-9-]+)\s*:\s*([^;]+);")

# Projects put their assets in different places; find rather than assume.
ASSET_DIRS = ("static", "static/css", "src/assets")


def _find(name: str) -> Path:
    for d in ASSET_DIRS:
        p = ROOT / d / name
        if p.exists():
            return p
    pytest.skip(f"{name} not found under {ASSET_DIRS} — no UI in this project?")


def _rules(path: Path) -> str:
    """CSS with comments stripped.

    A file is allowed to *describe* the rule it obeys. Scanning the comments too
    means the prose explaining "no hex literals here" counts as a hex literal —
    and the reflex fix is to delete the explanation.
    """
    return COMMENT_RE.sub("", path.read_text(encoding="utf-8"))


def _block(text: str, selector_re: str) -> str:
    m = re.search(selector_re + r"\s*\{(.*?)\n\s*\}", text, re.S)
    assert m, f"block {selector_re!r} not found — was brand.css restructured?"
    return m.group(1)


# --- app.css consumes the palette, it does not define one -------------------


def test_app_css_uses_semantic_tokens_only():
    hexes = HEX_RE.findall(_rules(_find("app.css")))
    assert not hexes, f"app.css must use semantic tokens, found hex literals: {hexes}"


def test_app_css_has_no_var_fallbacks():
    fallbacks = VAR_FALLBACK_RE.findall(_rules(_find("app.css")))
    assert not fallbacks, f"var(--x, fallback) is banned, found: {fallbacks}"


# --- the shared contract ----------------------------------------------------


def test_brand_css_keeps_the_seed_semantic_layer():
    """The semantic variable NAMES are the contract every project shares.

    If they drift, the dashboards stop being one system and app.css starts
    needing per-project special cases. Compared against this project's OWN copy
    of the skill — never an absolute path to someone's workspace, which would
    bake a personal path into a repo an external auditor may read.
    """
    seed = ROOT / ".claude" / "skills" / "brand-visuals" / "brand.css"
    if not seed.exists():
        pytest.skip("brand-visuals skill not vendored in this project")
    seed_names = set(SEMANTIC_RE.findall(seed.read_text(encoding="utf-8")))
    ours = set(SEMANTIC_RE.findall(_find("brand.css").read_text(encoding="utf-8")))
    assert seed_names, "no semantic tokens found in the seed — regex out of date?"
    assert not seed_names - ours, f"brand.css dropped seed tokens: {sorted(seed_names - ours)}"


def test_semantic_layers_carry_no_literal_colours():
    """Both semantic layers reference primitives only.

    The seed hardcoded ~20 hex values in its dark blocks and 16 more in light,
    which made skinning impossible to do the sanctioned way (primitives only).
    """
    text = _rules(_find("brand.css"))
    blocks = re.findall(
        r"(?:\[data-theme=\"(?:dark|light)\"\]|:root:not\(\[data-theme\]\))\s*\{(.*?)\n\s*\}",
        text,
        re.S,
    )
    assert len(blocks) == 3, f"expected light + 2 dark semantic blocks, found {len(blocks)}"
    for block in blocks:
        hexes = HEX_RE.findall(block)
        assert not hexes, f"semantic layer must reference primitives, found: {hexes}"


def test_both_dark_blocks_resolve_identically():
    """`[data-theme="dark"]` and the prefers-color-scheme block must agree.

    In the seed they were two hand-maintained copies of the same 20 values —
    one edit away from the manual toggle looking different from the OS default.
    """
    text = _rules(_find("brand.css"))
    blocks = re.findall(
        r"(?:\[data-theme=\"dark\"\]|:root:not\(\[data-theme\]\))\s*\{(.*?)\n\s*\}", text, re.S
    )
    assert len(blocks) == 2, f"expected 2 dark blocks, found {len(blocks)}"
    decls = [dict(DECL_RE.findall(b.replace("\n", " "))) for b in blocks]
    assert decls[0] == decls[1], "the two dark-theme blocks have drifted apart"


# --- the registry -----------------------------------------------------------


def _skins(text: str) -> dict[str, dict[str, str]]:
    """skin name -> {primitive: literal}. navy also lives on bare :root."""
    out = {}
    for m in re.finditer(r"\[data-skin=\"(\w+)\"\]\s*\{(.*?)\n\}", text, re.S):
        out[m.group(1)] = dict(DECL_RE.findall(m.group(2)))
    return out


def test_skin_registry_is_complete():
    """Every skin declares every primitive.

    A missing one silently inherits navy's value from :root and nobody notices
    until a screenshot looks wrong — the failure mode this whole file prevents.
    """
    skins = _skins(_rules(_find("brand.css")))
    assert len(skins) >= 2, f"expected a skin registry, found {sorted(skins)}"
    expected = set(skins["navy"])
    assert expected, "navy declares no primitives"
    for name, decls in skins.items():
        missing = expected - set(decls)
        assert not missing, f"skin {name!r} is missing {sorted(missing)}"
        stray = {k for k, v in decls.items() if not HEX_RE.fullmatch(v.strip())}
        assert not stray, f"skin {name!r} has non-literal primitives: {sorted(stray)}"


# --- contrast ---------------------------------------------------------------


def _luminance(h: str) -> float:
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    channels = []
    for i in (0, 2, 4):
        c = int(h[i : i + 2], 16) / 255
        channels.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    r, g, b = channels
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast(fg: str, bg: str) -> float:
    lo, hi = sorted((_luminance(fg), _luminance(bg)))
    return (hi + 0.05) / (lo + 0.05)


def _resolve(text: str, skin: str, theme: str) -> dict[str, str]:
    """Semantic token -> literal, as the browser would compute it."""
    primitives = _skins(text)[skin]
    selector = (
        r":root,\s*\[data-theme=\"light\"\]" if theme == "light" else r"\[data-theme=\"dark\"\]"
    )
    out = {}
    for name, value in DECL_RE.findall(_block(text, selector)):
        ref = re.fullmatch(r"var\((--[a-z0-9-]+)\)", value.strip())
        assert ref, f"{name} in the {theme} layer is not a plain var(): {value!r}"
        assert ref.group(1) in primitives, f"{name} -> {ref.group(1)} is not declared by {skin!r}"
        out[name] = primitives[ref.group(1)]
    return out


# Foreground, the backgrounds it actually renders on, and the WCAG minimum.
# AAA (7.0) for body text: these are financial dashboards read for hours.
# 3.0 for borders, which are UI component boundaries under WCAG 1.4.11.
PAIRS = [
    ("--text-primary", ["--bg-primary", "--surface", "--bg-secondary"], 7.0),
    ("--text-secondary", ["--bg-primary", "--surface", "--bg-secondary"], 4.5),
    ("--text-muted", ["--bg-primary", "--surface", "--bg-secondary"], 4.5),
    ("--accent-text", ["--bg-primary", "--surface", "--bg-secondary"], 4.5),
    ("--on-accent", ["--accent-primary", "--accent-hover", "--accent-active"], 4.5),
    ("--on-hero", ["--brand-hero"], 4.5),
    ("--on-hero-muted", ["--brand-hero"], 4.5),
    ("--brand-gold-text", ["--brand-gold"], 4.5),
    ("--status-success", ["--status-success-bg"], 4.5),
    ("--status-warning", ["--status-warning-bg"], 4.5),
    ("--status-danger", ["--status-danger-bg"], 4.5),
    ("--border-strong", ["--bg-primary", "--surface", "--bg-secondary"], 3.0),
    ("--focus-ring", ["--bg-primary", "--surface"], 3.0),
]


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_every_skin_meets_wcag_aa(theme):
    text = _rules(_find("brand.css"))
    failures = []
    for skin in sorted(_skins(text)):
        tokens = _resolve(text, skin, theme)
        for fg, bgs, need in PAIRS:
            for bg in bgs:
                got = _contrast(tokens[fg], tokens[bg])
                if got < need:
                    failures.append(
                        f"{skin}/{theme}: {fg} {tokens[fg]} on {bg} {tokens[bg]} "
                        f"= {got:.2f}, need {need}"
                    )
    assert not failures, "contrast failures:\n" + "\n".join(failures)


def test_status_hues_are_identical_in_every_skin():
    """A warning must look the same in every dashboard.

    Only status BACKGROUNDS shift per skin, so a pill sits on its canvas. If the
    foregrounds drifted, red would mean something slightly different per app —
    which is exactly the confusion the registry exists to remove.
    """
    text = _rules(_find("brand.css"))
    for theme in ("light", "dark"):
        seen = {}
        for skin in sorted(_skins(text)):
            tokens = _resolve(text, skin, theme)
            for token in ("--status-success", "--status-warning", "--status-danger"):
                seen.setdefault(token, {})[skin] = tokens[token]
        for token, by_skin in seen.items():
            assert len(set(by_skin.values())) == 1, f"{token} differs across skins: {by_skin}"


def test_geometry_rules_hold():
    """--radius: 0, no gradients, no shadows. Brand rules, not preferences."""
    for name in ("brand.css", "app.css"):
        text = _rules(_find(name))
        assert not re.search(r"\bgradient\(", text), f"{name} uses a gradient"
        assert not re.search(r"\bbox-shadow\s*:\s*(?!none)", text), f"{name} uses a shadow"
    assert re.search(r"--radius:\s*0\s*;", _rules(_find("brand.css"))), "--radius must be 0"
