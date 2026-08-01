# SKILL: brand-visuals

Trigger whenever a feature produces HTML, SVG, a dashboard, a chart, or any
visual artifact.

## Master theme — RKV is the default

`brand.css` in this skill folder is the master: the **RKV Strategic Advisory**
palette in a three-layer structure (primitives → semantic light → semantic
dark), with automatic and manual theme switching.

```
Deep Boardroom Navy #0E294E · Strategic Blue #1E56A0 · Muted Gold #D4AF37
Canvas light #F8F9FA · Canvas dark #07162C · Body #0A192F · Muted #5A6B82
Sharp geometry (--radius: 0), no gradients, no shadows.
```

On the first visual feature in a project, copy it verbatim into the project's
asset path (`static/brand.css` or `src/assets/brand.css`). Do not regenerate or
approximate the palette from memory — copy the file.

**RKV is the seed; a client skin is an explicit override.** If a project is
client-facing and needs client livery (TCS, Zuellig, …), edit only the
primitives in section 1 of the copied file and record the override as a
decision in ARCHITECTURE.md. `brand.tcs-example.css` in this folder is a worked
example of exactly that — a complete TCS-blue skin built on the same semantic
variable names. Never edit the semantic layer to change a color.

> Why this matters: until 2026-08-01 the master seed *was* the TCS theme, so
> every new project silently inherited client livery instead of RKV. A skin
> must be a deliberate act, never a default.

## Hard rule: colors are CSS variables, never inline hex

Reference the semantic variables everywhere — including when overriding
chart-library defaults:

```css
color: var(--text-primary);
background: var(--surface-elevated);
border-color: var(--border-subtle);
```

Never hardcode `#0e294e` etc. in markup or component styles; always go through
the variable so re-theming stays a single-file edit.

**No fallback values in `var()` for brand colors.** `var(--status-success,
#1a7f4b)` is an anti-pattern: the fallback is dead when the variable exists and
silently wrong when it doesn't match. Write `var(--status-success)`. If the
variable might be missing, that is a bug to fix in `brand.css`, not to paper
over at the call site.

## Theme switching

- Automatic: follows `prefers-color-scheme` when no `data-theme` attribute is set.
- Manual override: `<html data-theme="light">` / `<html data-theme="dark">`,
  persisted to `localStorage`.
- Ship **both** — automatic alone ignores an explicit user choice; manual alone
  ignores the OS preference on first load.

## Geometry & treatment

`--radius: 0` — sharp geometry is a brand rule, not a preference. No gradients,
no shadows. The only legitimate radius is `50%` on a circular status dot or
avatar. If a design seems to need a shadow, it needs a border
(`--border-subtle`) instead.

## Typography

- Headings: `--font-heading`. Body: `--font-body`. Mono: `--font-mono`.
- Defined as variables — reference them, never hardcode a font stack per
  component.

## Verifying compliance

Before closing any visual feature:

```bash
# Should return nothing but the primitives block in brand.css:
grep -rn "#[0-9a-fA-F]\{3,6\}" static/ src/ --include=*.css --include=*.js
```

Every hit outside `brand.css`'s section 1 is drift. This check is cheap and
catches the accumulation that made older projects need a cleanup pass
(one project reached 196 inline hex values despite carrying this very skill).

## Why this is a skill

One master file, copied per project and edited only at the primitive level,
means re-theming is a single-file edit and any external auditor sees brand
consistency rather than ad-hoc per-feature styling.

---
NO UI IN THIS PROJECT? Delete this skill folder.
CLIENT SKIN NEEDED? Edit section 1 primitives only; log it in ARCHITECTURE.md.
