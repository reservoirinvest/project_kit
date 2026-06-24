# ARCHITECTURE.md
*(Design decisions + standing principles. Updated only when a real decision is
made. An external auditor reads this as ground truth for "why it's built this way.")*

## Standing principles (every feature)
1. Core extraction is automatic and reported, not user-specified.
2. Idempotent operations — safe to re-run.
3. Fail loud, fail typed — specific exceptions, never bare Exception.
4. No hardcoded secrets or brand colors (externalized + swappable).
5. Caches are regenerable — never depend on a cache existing without a fetch path.
6. Explicit contracts between core and features.

## Brand visual spec (if project has UI)
Colors as CSS variables in one stylesheet so re-theming is a single edit.
Palette: {{BRAND_PALETTE_OR_DEFAULT}}
Geometry: border-radius 0, no gradients, no shadows unless specified.

## Decisions log
*(newest at bottom)*

### {{DATE}} — Scaffolding
Toolchain: {{PKG_MANAGER}} + {{LINTER}}. Git for version control with
hooks-enforced state-sync discipline, separate from any Drive sharing (Drive is
for human sharing; git is source of truth). Drive Desktop NOT pointed at the
live repo (stream-sync conflicts with working tree + venv churn).
