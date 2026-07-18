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

## Workflow
Two skills in `.claude/skills/` own the mechanics — follow them, don't
restate them:
- **`feature-build-loop`** — the canonical per-feature loop: spec-section
  targeting, core-vs-feature decision (yours to make and report), Plan Mode
  gate, ambiguity gate (2-3 named options, architecturally significant only),
  build → test → state files → risk flag → commit → compaction nudge.
- **`design-principles`** — the pattern catalogue + non-negotiables. Start
  every Plan Mode session from it.

State files: `spec.md` append-only (user-owned) · `PLAN.md` overwritten
(current state) · `PROGRESS.md` append-only log and the index you orient
from (never re-scan src/) · `ARCHITECTURE.md` decisions only, ≤1 paragraph
each. The PreCompact hook BLOCKS compaction if src/tests changed but
PLAN.md/PROGRESS.md weren't updated.

## Dependency management
- Source of truth: {{MANIFEST}} (managed by {{PKG_MANAGER}}).
- After every dependency change regenerate the lock-free export
  (`uv export --no-hashes --format requirements-txt > requirements.txt` or
  equivalent) so collaborators without {{PKG_MANAGER}} can install.

## Security
- `.secrets/` is git-ignored (enforced by .gitignore). Never print its
  contents into a response or commit message. Inventory for this project:
  - `.env` — {{SECRET_KEYS}}
  - {{OTHER_SECRET_FILES}}
- `.secrets/` may live in the Drive-shared copy if the user designates Drive
  as a secure channel — keep it out of git regardless (rules in `.driveignore`).
- No hardcoded secrets or brand colors anywhere.

## External auditors
{{AUDITORS}} may read this repo. Keep code self-documenting (docstrings, type
hints), keep ARCHITECTURE.md accurate (auditors read it as ground truth), and
leave no dead or commented-out code — deprecations get a cleanup feature
number the moment they're created.

## Framework gotchas
*(Fill in as they're discovered: framework-specific traps — restart-vs-rerun
rules, session-state hazards, theming constraints. See ibd's "Critical
patterns" section for the shape.)*

## LLM / external-API hygiene
- **Pin explicit model IDs** — never `*-latest` / `*-preview` aliases; they
  silently reroute (or exhaust a different quota bucket) with no log signal.
- **One live smoke test per provider** — real call, asserts the pinned model
  ID, `skipif` when the key is absent. Run manually before upgrading a model.
- **Keys in `.secrets/.env`** — a missing key raises a typed `RuntimeError`
  immediately (→ HTTP 503 at the endpoint), never a silent fallback. This
  includes optional providers (e.g. `CLAUDE_CODE_OAUTH_TOKEN` via
  `claude setup-token` — see README.md "OAuth Setup"): missing token = same
  typed error, no silent fallback to the API-key path.
- **Retry transient errors in the client layer only** — 3 attempts,
  2 s + 5 s backoff on 503/429; propagate auth/daily-quota errors
  immediately. The client-layer retry also covers chained (search→LLM)
  calls — never add an outer retry. Search APIs degrade gracefully: catch
  and append "(web search unavailable)" rather than failing the request.
