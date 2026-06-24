# SKILL: find-icon

Trigger when the user asks to "find an icon for X", "what icon should I use for Y",
or when a taxonomy/UI node needs an SVG icon that doesn't exist in `static/img/`.

## Priority order for icon sources

1. **Phosphor Icons** (primary) — all 256×256, `fill="currentColor"`, clean for
   dark-mode use. Browse at https://phosphoricons.com/. The `static/img/` folder
   already contains a curated subset. Before searching externally, grep the folder:
   ```
   ls static/img/*.svg | grep -i <keyword>
   ```
   Phosphor SVGs must have `viewBox="0 0 256 256"` — verify before using.

2. **SVG Repo** — https://svgrepo.com/ — large free library, mixed licences.
   Search for the concept, filter by licence (CC0 preferred). Always check the
   `viewBox` — the icon renderer in `src/utils/ecosystem.py` scales by `iw/256`,
   so a 64×64 icon will render at 1/4 the expected size. Normalise the coordinate
   space to 256×256 if needed (scale all path coords × 4, update viewBox).

3. **Icones.js** — https://icones.js.org/ — aggregates Phosphor, Material, Tabler,
   Heroicons and many others. Pick an icon, copy the SVG source.

4. **svgl** — https://svgl.app/ — brand / product logos only (company marks,
   framework badges). Not for generic UI icons.

## Normalising a non-256 SVG

If you download an icon with a different viewBox (e.g. `0 0 24 24`):
- Keep the `viewBox` as-is (it doesn't need to be 256×256).
- The renderer already reads the viewBox and scales correctly IF you update
  `icon_inner()` to use the actual viewBox size instead of hardcoding 256.
  Currently `ecosystem.py` line: `const s = iw / 256;` — if the icon is 24×24,
  change its wrapper to `scale(iw / 24)` or normalise the SVG to 256 coords.
- Easiest fix: in `static/img/`, save a 256×256 normalised version. Use
  `viewBox="0 0 256 256"` and scale path data by `256/original_size`.

## File format rules for `static/img/`

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="currentColor">
  <!-- no width/height attrs; no hardcoded fill colours; no <title> needed -->
  <path d="..."/>
</svg>
```

Strip: `fill="#000"`, `fill="#000000"`, `stroke="none"`, `width=`, `height=` attributes.
The `icon_inner()` function in `ecosystem.py` already strips `fill="#000"` but keep
files clean for future reuse.

## How `icon_inner()` works (don't break it)

```python
raw = path.read_text()
body = raw[raw.index(">", raw.index("<svg")) + 1 :]
body = body[: body.rindex("</svg>")]
body = body.replace('fill="#000000"', "").replace('fill="#000"', "")
```

It strips the outer `<svg>` wrapper and returns the inner path elements, which are
then placed inside an SVG `<g>` scaled to fit the node badge. Keep SVG files
single-root (one `<svg>` element, no nested `<svg>`).

## Checklist before committing a new icon

- [ ] `viewBox="0 0 256 256"` (or documented exception in `ARCHITECTURE.md`)
- [ ] No hardcoded fill colour (`fill="currentColor"` or no fill attr)
- [ ] No `width`/`height` attributes on the root `<svg>`
- [ ] Icon renders visibly inside a ~52px circle in the ecosystem canvas
- [ ] Filename is `kebab-case.svg` matching the concept (not a brand name unless it IS a logo)
- [ ] Entry added to `SECTOR_ICON` or node `"icon":` field in taxonomy
