# PROJECT STARTUP PROMPT (paste into Claude Code in a fresh, empty folder)

You are setting up a new, spec-driven, feature-by-feature project in this
currently-empty folder. I work from the CLI and grant you full control of this
ONE folder via git. Before writing anything, read this whole prompt, then
propose your setup plan and ASK my permission before creating files.

## How I work
- I add features incrementally to `spec.md` as `## Feature N: name` sections.
- I do NOT pre-declare a "Core" section. YOU decide per feature whether
  something is shared core/util vs. feature-specific (rule: would 2+ features
  plausibly need it?), build it in the right place, and REPORT the decision to
  me in your reply and in PROGRESS.md. Don't make me track this.
- Token economy matters — I don't want to burn my rate limit. Target spec
  sections precisely, use PROGRESS.md as the index of what exists instead of
  re-scanning the codebase, and keep PLAN.md current-state-only (overwritten)
  while PROGRESS.md is the only append-only log.

## What I want you to set up (ask before creating)
1. **State files**: CLAUDE.md (persistent instructions), PLAN.md (current
   state, overwritten), PROGRESS.md (append-only log), ARCHITECTURE.md
   (design decisions + standing principles), DOMAIN.md (project glossary /
   "memory" — facts you shouldn't have to re-derive), README.md (human-facing).
2. **`.claude/skills/`**: at minimum a `feature-build-loop` skill encoding the
   per-feature workflow, and a `brand-visuals` skill if this project produces
   any HTML/SVG/dashboards.
3. **`.claude/settings.json`** with:
   - Hooks: `PreCompact` (BLOCK compaction if src/tests changed but
     PLAN.md/PROGRESS.md didn't — exit 2 with instructions), `PostToolUse`
     (auto-format + git-stage edits), `Stop` (WIP safety commit),
     `SessionStart` (print PLAN.md + last PROGRESS.md entry + spec headings
     for free, so you don't spend a tool call re-orienting).
   - Permissions: allow git add/commit/status/diff/log, my toolchain, and
     writes scoped to this folder; ASK on git push/reset/branch -D/rebase,
     spec.md writes, and .env writes; DENY force-push and Read(.env).
4. **`.gitignore`** (excludes venv, caches, data artifacts, AND .env) and a
   **`.driveignore`** documenting a separate-folder Drive-share strategy
   (never point Drive Desktop at the live git working tree — it's slow and
   conflicts with the working tree + venv churn).
5. **Dependency manifest** for my toolchain, PLUS a generated
   `requirements.txt` (so collaborators without my tooling can install) that
   you regenerate after every dependency change.
6. **`.env` handling**: git-ignored always; safe to live in my Drive-shared
   copy (Drive is my secure channel); never print its contents.

## My toolchain & environment
- Package manager: {{PKG_MANAGER}}   (e.g. uv)
- Linter/formatter: {{LINTER}}        (e.g. ruff)
- Language/runtime: {{LANGUAGE}}      (e.g. Python 3.11+)
- IDE: {{IDE}}                        (e.g. Zed)
- OS: {{OS}}                          (e.g. Windows 11 — hooks must run as
  {{shell}}; convert .sh to .ps1/.cmd if bash isn't on PATH)
- External auditors: {{AUDITORS}}     (e.g. Google Antigravity agents may
  read this repo — keep code self-documenting, ARCHITECTURE.md accurate,
  no dead/commented-out code)
- Sharing channel: {{SHARING}}        (e.g. Google Drive, separate share folder)

## Model routing (advise me, and remind me when to switch)
- Default to the balanced mid-tier model for execution (writing standard code,
  tests, refactors).
- Recommend the top reasoning model (and Plan Mode) when a feature touches
  core, defines a schema/on-disk format, involves a multi-state model, or has
  2+ viable architectures with real tradeoffs.
- Reserve the frontier model for genuinely stuck problems where the mid and
  top models have both failed — it costs the most.
- Use the lightest model for trivial mechanical tasks (data transcription,
  mechanical renaming, single-line fixes).
- Tell me explicitly when you think I should switch models, and why.

**Task-type guide — apply per feature and per task within a feature:**

| Task type | Recommended model |
|-----------|-------------------|
| Schema / on-disk format definition | Opus + Plan Mode |
| New core abstraction (pluggable interface, provider pattern) | Opus + Plan Mode |
| Multi-state model (e.g. pending → accepted → dismissed) | Opus + Plan Mode |
| Feature-spanning algorithm / engine (weighting, scoring) | Sonnet + Plan Mode |
| Standard API endpoints, read paths, aggregations | Sonnet |
| UI components, modals, drill-down views | Sonnet |
| Write API + validation (decisions pre-resolved in spec) | Sonnet |
| CLI utility / checker (all checks enumerated in spec) | Sonnet |
| Data curation / seed authoring | Sonnet |
| Script entry point wiring (pyproject.toml + main function) | Sonnet |
| Mechanical transcription (copy-paste data into seed format) | Haiku |
| Genuinely stuck (mid + top both failed) | Opus 4.8 / Fable 5 |

Also add a `**Model:**` line to each `## Feature N` section in `spec.md` when you
write or update it, so the right model is chosen at feature-start without re-deriving it.

## When to use Plan Mode (tell me, don't silently use it)
Recommend Plan Mode before building when: the feature touches shared core,
introduces a new core abstraction, defines a data schema or on-disk format,
has a multi-state model, or is expensive to unwind if the first attempt is
wrong. Skip it for single-file features that only touch one feature folder.

## When to ask me vs. decide yourself
ASK (with 2-3 named options + tradeoffs) only on architecturally significant
ambiguity: state model, error-handling strategy, sync vs async, partial-failure
behavior, on-disk schema. DECIDE yourself (and note in ARCHITECTURE.md) for
naming, formatting, test structure, stdlib choices. Never ask about something
spec.md already states.

## When to compact
Proactively suggest /compact right after a feature is fully committed and
state files are synced — never mid-feature, mid-debug, or before tests pass.
The PreCompact hook enforces the sync; you suggest the timing.

## Brand / visual output (if this project has any UI)
All colors as CSS variables in a single brand stylesheet, never inline hex, so
re-theming is one file edit. Sharp geometry (border-radius 0), no gradients,
no shadows unless I say otherwise. Brand palette: {{BRAND_PALETTE_OR_DEFAULT}}

## Standing design principles to enforce every feature
Idempotent data operations (safe to re-run), fail-loud-fail-typed (specific
exceptions, not bare Exception), no hardcoded secrets or brand colors, treat
caches as regenerable (never depend on a cache existing without a fetch path),
keep the public contract between core and features explicit, and wire a
`[project.scripts]` entry in `pyproject.toml` on first setup so `uv run
<project-name>` is the canonical start command — never document a raw uvicorn
or python invocation as primary.

---

Now: confirm you've read this, tell me your proposed file list and the
core-vs-feature/model/Plan-Mode conventions you'll follow, FLAG anything you'd
do differently or any best practice I'm missing, and ASK my permission before
creating any files. After I approve, create everything, then run the git init
+ first commit + dependency install, and tell me the exact next command to run.
