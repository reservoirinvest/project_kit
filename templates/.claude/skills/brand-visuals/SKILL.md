# SKILL: brand-visuals

Trigger whenever a feature produces HTML, SVG, a dashboard, a chart, or any
visual artifact.

## The registry — pick a skin, never edit a colour

`brand.css` in this folder is the master. It carries the **RKV Strategic
Advisory** palette in five named skins, and a project selects one with a single
attribute:

```html
<html lang="en" data-skin="amethyst">
```

| Skin | Hue | Assigned to |
|------|-----|-------------|
| `navy` | 215° | **default** — applies with no `data-skin` at all |
| `indigo` | 240° | `kite` (8120) |
| `amethyst` | 268° | `ibf` (8020) — the app that can place live trades |
| `teal` | 185° | **reserved** — Zuellig livery (`zp_scm`, `#005d62`) |
| `slate` | 220°, desaturated | `mktdb` (8000) |

One dashboard per skin. Register the pairing in `PORTS.md` when you claim one.

Cool hues only. Green, amber and red are the **status** palette; a skin in
those families competes with status meaning, so none is offered. Status
foregrounds are byte-identical in every skin — a warning must look the same in
every dashboard — and only their backgrounds shift to sit on the skin's canvas.

> Why this exists: every dashboard rendered in the same navy, and with five
> open you could not tell which tab was which. One of them places live trades,
> so this is a safety property, not a cosmetic one.

## Copy it, never edit it

On the first visual feature, copy `brand.css` verbatim into the project's asset
path (`static/brand.css`, `static/css/brand.css`, or `src/assets/brand.css`).
Copy `skins.py` next to it in `.claude/skills/brand-visuals/` too.

**`brand.css` is generated and byte-identical in every project.** Do not
hand-edit it, in the kit or in a project. To change or add a palette:

```bash
cd .claude/skills/brand-visuals && python skins.py   # rewrites brand.css
```

Then re-run `_project_kit/sync-skills.ps1 -Apply` to fan it out. Because the
file is identical everywhere, drift between projects is now detectable by hash
rather than by eye.

**A client livery is a new `[data-skin="<client>"]` entry in `skins.py`'s
`SKINS` table**, plus a decision recorded in ARCHITECTURE.md — not an edit
anywhere else. `brand.tcs-example.css` is retained as a worked example of the
older hand-skinned form; read it for the shape, don't copy the method.

## The three layers, and the line between them

1. **Primitives** (`--rk-light-*`, `--rk-dark-*`) — the *only* place a colour
   literal may appear.
2. **Semantic** (`--text-primary`, `--surface`, `--status-danger`, …) — the
   names are the contract shared across every project. They never change; only
   primitives do. Every value is a plain `var()`.
3. **Base** — element defaults.

Both semantic layers reference primitives, so a skin covers light *and* dark.
The dark theme was promoted first (ibf, 2026-08-02); light followed when the
registry landed. Before that the semantic layer held ~36 literals, which made
skinning impossible to do the sanctioned way.

## Hard rule: colors are CSS variables, never inline hex

```css
color: var(--text-primary);
background: var(--surface);
border-color: var(--border-subtle);
```

**No fallback values in `var()`.** `var(--status-success, #1a7f4b)` is an
anti-pattern: the fallback is dead when the variable exists and silently wrong
when it doesn't match. With five skins it cannot be right for more than one of
them. If a variable might be missing, that is a bug to fix in `brand.css`, not
to paper over at the call site — and in JS, report the missing token loudly
rather than substituting a literal (see `kite/static/app.js:graphTheme`).

### Surface-specific foregrounds

Text takes its colour from the surface it sits on, not from the page:

| Surface | Foreground |
|---------|------------|
| `--bg-primary` / `--surface` / `--bg-secondary` | `--text-primary` / `--text-secondary` / `--text-muted` |
| `--brand-hero` (the app header slab) | `--on-hero` / `--on-hero-muted` |
| `--accent-primary` (a filled button) | `--on-accent` |

Using `--text-inverse` on the hero is the specific mistake the old seed forced:
in dark mode it resolved to 1.10:1, an invisible header. `--text-inverse` means
"text on an inverted surface" and belongs nowhere else.

## Theme switching

- Automatic: follows `prefers-color-scheme` when no `data-theme` is set.
- Manual: `<html data-theme="light">` / `"dark"`, persisted to `localStorage`.
- Ship **both** — automatic alone ignores an explicit choice; manual alone
  ignores the OS preference on first load. `ibf/static/js/theme.js` is the
  reference three-state auto → light → dark toggle.

`data-skin` and `data-theme` are independent attributes: a skin defines both of
its themes.

## Geometry & treatment

`--radius: 0` — sharp geometry is a brand rule, not a preference. No gradients,
no shadows. The only legitimate radius is `50%` on a circular status dot. If a
design seems to need a shadow, it needs a border (`--border-subtle`).

## Typography

Headings `--font-heading`, body `--font-body`, mono `--font-mono`. Reference
them; never hardcode a font stack per component.

## Verifying compliance

Copy `tests/test_brand_css.py` from the kit into the project. It enforces all of
the above, including **WCAG contrast for every skin in both themes** — AAA for
body text, AA for secondary and status, 3:1 for borders as UI component
boundaries. These are financial dashboards read for hours; a pretty palette
that fails on muted text is not usable.

```bash
uv run pytest tests/test_brand_css.py
grep -rn "#[0-9a-fA-F]\{3,6\}" static/ --include=*.css   # only brand.css §1b should hit
```

The tests deliberately do not import `skins.py` — a generator that graded its
own homework would pass whatever it produced.

---
NO UI IN THIS PROJECT? Delete this skill folder.
CLIENT SKIN NEEDED? Add a `SKINS` row in `skins.py`, regenerate, log it in ARCHITECTURE.md.
