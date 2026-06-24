# SKILL: brand-visuals

Trigger whenever a feature produces HTML, SVG, a dashboard, a chart, or any
visual artifact.

## Hard rule: colors are CSS variables, never inline hex
Define the palette ONCE in `src/assets/brand.css` (create on the first visual
feature) and reference variables everywhere — including overriding chart-library
default colors. This is what makes re-theming a single-file edit.

```css
:root {
  --brand-primary:   {{HEX}};  /* dominant — headers, anchors */
  --brand-secondary: {{HEX}};  /* sub-headers, containers, states */
  --brand-accent:    {{HEX}};  /* SPARINGLY — alerts, thresholds only */
  --brand-canvas:    {{HEX}};  /* light background */
  --brand-dark:      {{HEX}};  /* dark canvas — dividers, frames */
  --brand-text:      {{HEX}};  /* primary readable text */
  --brand-muted:     {{HEX}};  /* captions, footnotes, secondary copy */
}
```

## Geometry & treatment (adjust to your brand)
- Default: sharp geometry — `border-radius: 0`, no gradients, no drop shadows,
  solid borders. Override only if your brand guide says otherwise.
- Tints: for contrast without a new hue, use tints (10–90%) of primary or
  secondary only. Never introduce off-palette colors.

## Typography intent
- Headlines: your display face, consistent casing + tracking.
- Body/code: a clean, legible sans.
- Accent color is for data emphasis only, never decoration.

## Why this is a skill
Consistent, variable-driven output means re-theming is one CSS edit, and any
external auditor sees brand consistency rather than ad-hoc per-feature styling.

---
TO CUSTOMIZE: replace {{HEX}} values with your palette, or delete this skill
if the project has no UI.
