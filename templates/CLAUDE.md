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

## Model routing
Pick per feature (per task within a feature, if it's a mixed-complexity
feature) and record it as a `**Model:**` line in that feature's spec.md
section — see the `feature-build-loop` skill for when in the loop this
happens. Tell the user explicitly when you think they should switch models,
and why; never silently assume.

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
| Script entry point wiring (manifest + main function) | Sonnet |
| Mechanical transcription (copy-paste data into seed format) | Haiku |
| Genuinely stuck (mid + top models both failed) | Opus / Fable |

Reserve Fable for genuinely stuck problems after both Sonnet and Opus have
failed — it costs the most. Use Haiku only for trivial mechanical work, never
for anything touching `src/core/` or a schema decision.

## How this project is run
The canonical command is **`uv run {{PROJECT_NAME}}`**, from the
`[project.scripts]` entry in `pyproject.toml`. Wire it on first setup, before
the first feature ships — retrofitting it means rewriting every command in
every doc, and stale `python -m` invocations survive in files nobody reopens.

- Never document `uv run python -m src.<module>`, `uvicorn ...` or a bare
  `python` invocation as the primary way to run this. They are implementation
  detail and they break the moment a module moves.
- Subcommands and flags hang off that one command
  (`uv run {{PROJECT_NAME}} --pptx`, `uv run {{PROJECT_NAME}} serve`), so
  there is exactly one thing to remember and one place to document.
- The entry point needs a real `[build-system]` and the project installed
  (editable) — `uv sync` does that. Without it `uv run {{PROJECT_NAME}}` is
  "command not found", which reads as a broken checkout.
- `uv run pytest` / `uv run ruff check .` are the exceptions: those are tool
  invocations, not this project's entry point.

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
