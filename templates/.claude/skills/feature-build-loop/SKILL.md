# SKILL: feature-build-loop

Trigger this whenever Kashi says "build Feature N", "start the next feature",
"implement spec Feature N", or points at a new `## Feature N` section in spec.md.

This is the canonical loop. Follow it in order. Do not skip steps under
context pressure — the PreCompact hook will block compaction if PLAN.md /
PROGRESS.md fall out of sync, so skipping is wasted effort anyway.

## The loop

1. **Read only the relevant spec section.** Jump to the specific `## Feature N`
   heading in spec.md. Do NOT re-read earlier features — PROGRESS.md is the
   index of what already exists. Do NOT re-scan all of src/.

2. **Core-vs-feature decision (your call, reported, not Kashi's to pre-specify).**
   Ask internally: would 2+ features plausibly need this? If yes → it goes in
   `src/core/` (shared logic) or `src/utils/` (pure helpers), named generically.
   If no → `src/features/<slug>/`. State the decision in your reply AND in the
   PROGRESS.md entry.

3. **Plan Mode gate.** If the feature touches src/core/, introduces a new core
   abstraction, has a multi-state model, has 2+ viable architectures, or makes
   an expensive-to-unwind decision (schema, on-disk format, public contract)
   → STOP and say: "This warrants Plan Mode because [reason]. Recommend the
   top reasoning model for the planning session." Wait for Kashi. Start the
   planning session from the `design-principles` skill's pattern catalogue —
   reuse a proven pattern before inventing one.

4. **Ambiguity gate.** If spec.md is unclear on something architecturally
   significant (state model, error strategy, sync/async, partial-failure
   behavior) → ask, presenting 2-3 named options with tradeoffs. Do NOT ask
   about naming, formatting, or anything spec.md already states.

5. **Build.** Use `uv add <pkg>` for new deps (never hand-edit requirements.txt
   or pyproject deps). After any dep change, regenerate:
   `uv export --no-hashes --format requirements-txt > requirements.txt`

6. **Test.** Write tests in tests/ mirroring src/ layout. Run
   `uv run pytest` and `uv run ruff check .` Both must pass before "done".

7. **Update state files (the part the PreCompact hook enforces):**
   - PLAN.md: overwrite the current-feature section (current state only, not a log)
   - PROGRESS.md: append one tight paragraph — feature name, what was built,
     files touched, core-vs-feature call, deviations from spec
   - ARCHITECTURE.md: ONLY if a real design decision was made this cycle,
     and ≤1 paragraph per decision (what was decided, why, what was
     rejected). Implementation narrative goes in PROGRESS.md, not here.
   - README.md: ONLY if entrypoints / setup changed

8. **Design-principle flag (2-3 lines max).** Note any risk: tight coupling,
   missing error boundary, untested edge, spec drift. Flag, don't lecture.

9. **Commit.** `git add -A && git commit -m "feat(feature-N): <summary>"`

10. **Compaction nudge.** If context feels heavy AND the feature is fully
    committed: "Feature N committed, state files synced — good point to
    /compact before Feature N+1." Never nudge mid-feature or before tests pass.

## Token-economy reminders (apply throughout)
- Don't re-read whole spec.md once multi-feature — target the heading.
- Don't re-scan src/ — use PROGRESS.md as the index, grep specific files.
- PLAN.md is overwritten; PROGRESS.md is the only append-only log.
