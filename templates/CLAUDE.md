# Project: {{PROJECT_NAME}}

Persistent instructions. Re-read at every session start (the SessionStart hook
prints PLAN.md + last PROGRESS.md entry automatically — follow this file).

## Identity & stack
- Language/runtime: {{LANGUAGE}}
- Package manager: {{PKG_MANAGER}} (never bypass it for ad-hoc installs)
- Lint/format: {{LINTER}} (auto-runs on Edit/Write via PostToolUse hook)
- IDE: {{IDE}}
- Git: full repo control granted. Plain commits, no force-push, no history
  rewrites without asking.

## The Core/Feature split — YOU decide this, not the user
The user adds `## Feature N: name` sections to spec.md. Per feature:
1. Ask: would 2+ features plausibly share this? If yes → it's core/util.
2. If yes → build under `src/core/` (shared logic) or `src/utils/` (pure
   helpers), named generically for what it does, not for the triggering feature.
3. If a later feature needs something similar → extend the core module, don't
   fork a copy.
4. REPORT the core-vs-feature decision in your reply AND PROGRESS.md. The user
   does not pre-specify this in spec.md — it's your call to make and report.
5. Feature code lives in `src/features/<slug>/`.

## Workflow per feature
Follow the `feature-build-loop` skill in `.claude/skills/`. Summary:
read the relevant spec section only → core-vs-feature decision → Plan Mode
gate → ambiguity gate → build → test → update PLAN.md (overwrite) + PROGRESS.md
(append) + ARCHITECTURE.md (if a decision was made) + README.md (if setup
changed) → flag design risks (2-3 lines) → commit → suggest /compact if heavy.

## Dependency management
- Source of truth: {{MANIFEST}} (managed by {{PKG_MANAGER}}).
- Maintain a generated `requirements.txt` (or equivalent lock-free export) so
  collaborators without {{PKG_MANAGER}} can install. Regenerate after every
  dependency change. It goes in the Drive allow-list; the virtualenv never does.

## When to recommend Plan Mode (say it explicitly, don't silently use it)
Feature touches src/core/, introduces a new core abstraction, defines a schema
or on-disk format, has a multi-state model, or is expensive to unwind. Skip for
single-file features in one feature folder. Recommend the top reasoning model
for genuinely architectural planning sessions; the mid-tier model is fine for
execution.

## When to ask vs decide
ASK (2-3 named options + tradeoffs) only on architecturally significant
ambiguity: state model, error strategy, sync/async, partial-failure behavior,
on-disk schema. DECIDE yourself (note in ARCHITECTURE.md) for naming,
formatting, test structure. Never ask what spec.md already states.

## Compaction discipline
The PreCompact hook BLOCKS compaction if src/tests changed but
PLAN.md/PROGRESS.md weren't updated. Proactively suggest /compact right after a
feature is committed and synced — never mid-feature, mid-debug, or before tests
pass.

## Token economy
- Don't re-read whole spec.md once multi-feature — target the `## Feature N`
  heading.
- Don't re-scan src/ to start a feature — use PROGRESS.md as the index, grep
  specific files.
- PLAN.md is overwritten (current state only); PROGRESS.md is the only
  append-only log.

## Security
- `.env` is git-ignored (enforced by .gitignore + a Read(.env) permission
  deny). Never print its contents into a response or commit message.
- `.env` may live in the Drive-shared copy if the user designates Drive as a
  secure channel — keep it out of git regardless.
- No hardcoded secrets or brand colors anywhere.

## External auditors
{{AUDITORS}} may read this repo. Keep code self-documenting (docstrings, type
hints), keep ARCHITECTURE.md accurate (auditors read it as ground truth), and
leave no dead or commented-out code.

## Standing design principles
Idempotent operations (safe to re-run), fail-loud-fail-typed (specific
exceptions), caches are regenerable (never depend on one existing without a
fetch path), explicit core↔feature contracts, brand colors as CSS variables.
