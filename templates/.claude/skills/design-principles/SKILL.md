# SKILL: design-principles

Trigger this at every Plan Mode session, and whenever a feature introduces a
new core abstraction, schema / on-disk format, external provider, AI-proposed
write path, or multi-state model. Start architectural thinking from this
catalogue — do not rediscover these patterns from scratch.

Distilled from mktdb (primary), zp_scm, ibd, and the project kit.

---

## 1. Non-negotiable principles (checklist — every feature)

1. **Idempotent operations.** Every seed, sync, export, scan, and migration is
   safe to re-run. If re-running produces a different outcome, that's a bug.
2. **Fail loud, fail typed.** Specific exception classes, never bare
   `Exception`. A missing API key raises a typed `RuntimeError` immediately
   (surfacing as HTTP 503 at an endpoint), never a silent fallback.
3. **Regenerable caches.** Nothing depends on a cached artifact existing
   without a code path that regenerates it; generated artifacts live in a
   git-ignored `output/` tree and are rebuilt on the fly if absent.
4. **Explicit core↔feature contracts.** Shared logic in `src/core/`, pure
   helpers in `src/utils/`, feature code in `src/features/<slug>/`. The
   core-vs-feature call is Claude's to make and *report*, per feature.
5. **No hardcoded secrets or brand colors.** Keys in git-ignored `.secrets/.env`;
   colors as CSS variables defined once in `:root`.
6. **Pin explicit model IDs.** Never `*-latest` / `*-preview` aliases —
   they silently reroute (and can burn a different quota bucket) with no log
   signal.

---

## 2. Architecture patterns (proven; reuse before inventing)

### 2.1 Pluggable provider: ABC + factory, config read per call
Abstract base (`LLMClient` / `SearchClient` style) + concrete subclasses + a
`get_*_client()` factory that reads config **on every call** — no
module-level singleton. A config PATCH takes effect on the next request
without a restart. Adding a provider = one subclass, one factory branch, one
allow-list entry (validated → typed 422 otherwise). SDKs imported lazily
inside the subclass.

### 2.2 Two-track AI writes: insights vs recommendations
An automated scan **never mutates an entity directly**:
- **Insights** — read-only observations (url/title/summary), auto-saved,
  deduped on `(entity_id, source_url)`. Safe because they alter nothing.
- **Recommendations** — machine-proposed field changes stored
  `status=pending`. Human **accept** is the only path that writes the entity.
Accepted/dismissed recommendations are preserved as history on overwrite —
they are decisions, not regenerable output.

### 2.3 Whitelisted, type-coerced apply
Any machine-proposed write may only target a per-entity **field whitelist**;
values are coerced to the column type (enum, float) and rejected with a typed
422 otherwise. The LLM prompt is constrained to the same whitelist and
non-conforming proposals are filtered at parse time — defense on both sides.

### 2.4 Fail-soft only on regenerable output
Malformed LLM JSON → zero recommendations, but the insights are never lost
(tolerant parser returns `[]`). Everything non-regenerable stays fail-loud.
Corollary for bulk sweeps: **per-entity failure isolation** — rollback +
collect in an `errors` list; one bad entity never aborts the sweep.

### 2.5 Retry lives in the client layer, once
Transient provider errors (503/429) get retry-with-backoff (3 attempts,
2 s + 5 s) **inside the provider client**; auth/quota errors propagate
immediately. Outer feature code never adds a second retry — the client-layer
retry also covers chained (search → LLM) calls.

### 2.6 Surface separation for auditability
Read, write, and automation are separate routers with separate schema
modules, so an auditor sees each contract as a distinct thing. Write model:
**per-row save-on-commit** — one request per row, errors inline on that row,
deliberately no bulk/transactional "save all" (removes partial-failure
ambiguity; every write idempotent and individually reversible).

### 2.7 Additive-only auto-migration
New columns are nullable (or carry a `server_default`) and auto-added by a
startup `_migrate_add_columns`; new tables via `create_all`. Anything
non-additive is an explicit, called-out drop+recreate from the idempotent
seed — never a silent one. (Known limit: no ALTER/rename/drop support; adopt
Alembic only when a project outgrows this.)

### 2.8 Content as data, not layout
- **Sections are rows**: page sections carry a `block_type` discriminator +
  editable `display_order`; the view sorts and dispatches. Reordering or
  removing a section is a data edit, not a code change.
- **Registry pattern**: ordered `[{file, label}]` registries (docs,
  providers) — adding an entry is a one-line data addition.
- **File-or-inline narrative, resolved server-side**: a row's prose comes
  from `body` or a markdown file under a sandboxed docs dir; the endpoint
  returns `resolved_body` with the precedence rule centralized, a
  path-traversal guard, and silent fallback to inline when the file is
  absent.
- **Per-entity Markdown as source of truth**: YAML frontmatter for typed
  fields + `##` prose sections, with load/dump helpers and an integrity
  check enforcing parse/enum/coverage sanity.

### 2.9 Master taxonomy superset + fork subsets
The master repo holds the superset; forks hold scoped subsets kept aligned by
an AST-literal diff tool (diffs two repos without importing them) + a sync
skill. If a fork outgrows its placement in a fixed-depth model, **promote to
a new top-level unit** rather than deepening the hierarchy. Fork-local config
(URLs, keys) lives in each fork's `config.yml`, never in the shared seed.

### 2.10 Documented planning constants
When live data isn't warranted (FX rates, margin estimates), use a **named
constant with its provenance and refresh policy documented**, render derived
values visibly as estimates ("~US$X (est.)"), preserve the source figure for
traceability, and keep every estimate user-overridable.

### 2.11 Read-only integrity checker
A sweep returning per-check pass/warn/fail, exposed as CLI (non-zero exit on
fail) and endpoint. Reads enum/FK columns with column-only/raw-SQL queries so
illegal data is *reported*, not crashed on. `--fix` deletes only orphaned
child/join rows. Rule: **every new write path adds a check here.**

### 2.12 Offline-first assets and export
- Vendor JS/icons locally (no CDN); icons use `fill="currentColor"` for
  theme-adaptive light/dark; provenance recorded in `SOURCES.md`.
- Self-contained export: bake API payloads byte-identical via an in-process
  test client into `window.__DATA__`, add a fetch shim + asset rewriter in a
  head bootstrap so the main JS runs **unchanged**; hide server-only UI with
  injected CSS. One template serves embedded (iframe) and standalone.

---

## 3. Process rules layered on the feature-build-loop

- **ARCHITECTURE.md entries are ≤ 1 paragraph per decision** — what was
  decided, why, what was rejected. Implementation narrative belongs in
  PROGRESS.md. Auditors read ARCHITECTURE.md as ground truth; keep it
  findable.
- **Feature accounting**: work that supersedes an old feature's presentation
  or behavior is a **new feature**, not a reopen — the old feature stays
  COMPLETE and its contracts are reused unchanged where possible. Record
  rejected alternatives with the reason.
- **Cleanup cadence**: anything marked legacy gets an owner "Feature N:
  cleanup" at the moment it is deprecated. Run a cleanup cycle every ~5
  features or before any external review — legacy must not accumulate.
- **Root-cause over symptom**: debugging lands on the mechanism and the
  mechanism is written down. One live smoke test per external provider
  asserts the pinned model ID (`skipif` when the key is absent).
- **Framework gotchas** (brownfield / UI-heavy apps): keep a "Critical
  patterns" section in the project CLAUDE.md for framework-specific traps
  (restart-vs-rerun rules, session-state hazards, theming constraints).
  Brownfield apps adopt the state-file quartet + hooks even when the
  `src/core|features` layout doesn't fit.
