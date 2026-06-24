# SKILL: find-icon

Trigger when the user asks to "find an icon for X", "what icon should I use for Y",
or when a taxonomy/UI node needs an SVG icon that doesn't exist in `static/img/`.

## Priority order for icon sources

1. **Phosphor Icons** (primary) — all 256×256, `fill="currentColor"`, clean for
   dark-mode use. GitHub raw: `https://raw.githubusercontent.com/phosphor-icons/core/main/assets/regular/<name>.svg`.
   The `static/img/` folder already contains a curated subset — grep it first:
   ```
   ls static/img/*.svg | grep -i <keyword>
   ```

2. **svgl** — https://svgl.app/ — brand / product **logos** only (company marks,
   framework badges). Use this when the target IS a brand logo, not a generic icon.

3. **SVG Repo** — https://svgrepo.com/ — large free library, mixed licences.
   Filter by CC0. Always check `viewBox` — a 24×24 icon needs normalising (see below).

4. **Icones.js** — https://icones.js.org/ — aggregates Phosphor, Material, Tabler,
   Heroicons and others. Good fallback when Phosphor has no match.

## How to download icons — USE BASH, NOT WebFetch+Write

**Never** use `WebFetch` + `Write` for icon files. That loads SVG content into the
context window unnecessarily. Use a single `Bash` call with `curl` instead:

```bash
# Single icon
curl -sL "https://raw.githubusercontent.com/phosphor-icons/core/main/assets/regular/trophy.svg" \
  -o "static/img/trophy.svg"

# Multiple icons at once (far more efficient)
for icon in flag-checkered trophy dna fish megaphone buildings; do
  curl -sL "https://raw.githubusercontent.com/phosphor-icons/core/main/assets/regular/$icon.svg" \
    -o "static/img/$icon.svg"
done
```

For svgl/SVGRepo, find the direct CDN URL for the SVG and curl it the same way.
Only use `WebFetch` if you need to *inspect* page content to find the right URL
(e.g. scraping an svgrepo search result). Once you have the direct `.svg` URL, curl it.

## Normalising a non-256 SVG

If you download an icon with a different viewBox (e.g. `0 0 24 24`):
- Keep the `viewBox` as-is — it doesn't need to be 256×256.
- The renderer reads the viewBox and scales correctly IF `icon_inner()` uses the
  actual size. Currently `ecosystem.py` hardcodes `iw / 256` — if the icon is 24×24,
  normalise path coords × (256/24) and set `viewBox="0 0 256 256"`.
- Easiest: normalise to 256×256 in `static/img/`. Scale all path coordinates by
  `256 / original_size`.

## File format rules for `static/img/`

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="currentColor">
  <!-- no width/height attrs; no hardcoded fill colours; no <title> needed -->
  <path d="..."/>
</svg>
```

Strip: `fill="#000"`, `fill="#000000"`, `stroke="none"`, `width=`, `height=` attributes.
`icon_inner()` strips `fill="#000"` at runtime, but keep files clean for reuse.

## How `icon_inner()` works (don't break it)

```python
raw = path.read_text()
body = raw[raw.index(">", raw.index("<svg")) + 1 :]
body = body[: body.rindex("</svg>")]
body = body.replace('fill="#000000"', "").replace('fill="#000"', "")
```

Extracts inner path elements, strips the outer `<svg>` wrapper, and places them
inside a scaled `<g>`. Keep SVG files single-root (one `<svg>`, no nested `<svg>`).

## Checklist before committing a new icon

- [ ] `viewBox="0 0 256 256"` (or documented exception in `ARCHITECTURE.md`)
- [ ] No hardcoded fill colour (`fill="currentColor"` or no fill attr)
- [ ] No `width`/`height` attributes on the root `<svg>`
- [ ] Icon renders visibly inside a ~52px circle in the ecosystem canvas
- [ ] Filename is `kebab-case.svg` matching the concept (not a brand name unless it IS a logo)
- [ ] Entry added to `SECTOR_ICON` or node `"icon":` field in taxonomy
