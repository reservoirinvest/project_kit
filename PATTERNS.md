# PATTERNS.md — the RKV engineering canon

Decided conventions, each with the reason it exists. This is the standard
`/advisor` audits against: a project that diverges is drift, not preference.

**How a pattern gets in here:** it was built twice, or built once and cost real
debugging to get right. Say *"enshrine X"* in any session and it lands here,
generalized, with the failure that motivated it recorded. A pattern with no
recorded failure is a style opinion — leave it out.

**Status key:** `canon` = do this · `emerging` = one good implementation,
promote on the next use · `anti` = actively avoid.

---

## 1. LLM provider layer — `canon`

**Shape.** One `LLMClient` ABC per project, in a single module. Concrete
clients per provider. SDK imports are **deferred into `__init__`**, so an
unused provider needs no install. An ordered registry defines both resolution
and UI display order. `get_client()` re-reads config per call, so switching
providers needs no restart.

**Pin explicit model IDs.** Never `*-latest` or `*-preview` — they reroute
silently, sometimes into a different quota bucket, with no log signal.

**Missing key fails at construction**, typed: `LLMUnavailable(f"{env_key} is
not set — {hint}")`, a `RuntimeError` subclass, surfaced as HTTP 503. The hint
must be actionable (`"add it to .secrets/.env"`, ``"run `claude setup-token`"``).
Never a silent fallback to another provider — a silent fallback means you are
billed and answered by something you did not choose.

**Retry transient only.** 3 attempts, 2 s then 5 s. Transient tokens:
`503, UNAVAILABLE, 429, RESOURCE_EXHAUSTED, overloaded`. Auth failures and
exhausted daily quotas propagate immediately — retrying them just delays the
error. Idiom: `for delay in (*_RETRY_BACKOFF, None)`, where `None` marks the
final attempt. Retry lives in the client layer only; never add an outer retry
around a chained search→LLM call.

**Report the observed outcome, not the request.** If web search was asked for
and the provider cannot do it, the response says so
(`"{provider} cannot search the web — answered from local data only."`).
Degradation is fine; pretending is not.

### 1a. The two-endpoint rule — `canon`

"A key is present" and "the key works" are different questions. Ship both:

| Endpoint | Cost | Answers |
|---|---|---|
| `GET /api/ask/providers` | free, local | is the env var set, what model, does it support web |
| `POST /api/ask/test` | one real round-trip | does it actually work |

`/test` sends a fixed trivial prompt (*"Reply with the single word: OK"*) and
**never raises** — it returns `{provider, ok: false, detail}` on every failure
path, including bare `Exception`. A test endpoint that can throw is a test
endpoint that tells you nothing on the day it matters.

> **Why:** this is what caught `ANTHROPIC_API_KEY` being present, valid, and
> having a zero credit balance. Key-presence checks said green. Only a real
> round-trip found it. That provider was then *removed from the menu* rather
> than left as a guaranteed-broken entry.

### 1b. Ask AI config surface — `canon`

Persistent settings belong in **Config**, not in the Ask panel. A setting that
lives next to the thing it configures gets set once and lost on reload.

- Provider choice and web-search toggle are config keys (`LLM_PROVIDER`,
  `LLM_WEB_SEARCH`), in `EDITABLE_KEYS`, rendered in the Config tab.
- Each provider row shows: model ID, configured/unconfigured chip, and a
  **Test** button writing `✓ <model> replied <text>` or `✗ <detail>` inline,
  with the full detail in `title=`. Cache results in UI state so they survive
  a re-render.
- **Test results are per-provider and never global.** "The LLM is down" is not
  a thing; "gemini is rate-limited" is.

**Assert the allow-list is reachable.** Any key in `EDITABLE_KEYS` that no UI
renders is a key that can only be changed by hand-editing YAML — a trap. Write
the test: `EDITABLE_KEYS ⊆ rendered config fields`.

### 1c. Follow-ups — `canon`

Two different things, both capped at 5, **never conflated**:

1. **Thread budget** — how many prior turns are carried as context.
   `ASK_HISTORY_MAX`.
2. **Suggested follow-up chips** — up to 5 model-generated next questions
   rendered after each answer. `ASK_FOLLOWUPS_MAX`.

Both caps live in config and reach the frontend through `/api/config`.
**Never duplicate a cap as a constant in both Python and JS** — that pair
drifts, and the comment saying "mirrors the other one" is the tell.

### 1d. Provider lessons paid for in debugging — `canon`

- **Claude Agent SDK raises after succeeding.** It can raise
  `"Claude Code returned an error result: success"` *after* delivering a
  complete answer (`is_error=False`, `subtype='success'`). Drain the stream,
  keep the parts, and let **the received text decide the outcome** — not the
  exception.
- **The spawned CLI prefers a visible `ANTHROPIC_API_KEY`.** `env=` passed to
  the SDK is *merged* with the parent environment, not replaced. With a
  zero-balance key visible, the CLI returned the literal string
  *"Credit balance is too low"* as the assistant's answer. Pop the variable for
  the duration of the call, restore it in `finally` — including on the raising
  path.
- **Thinking models silently return empty.** `gemini-2.5-flash` spends the
  output budget on thinking tokens and returns nothing with
  `finish_reason=MAX_TOKENS`. Set `thinking_budget=0` on the **ungrounded**
  path only — grounded/search calls need thinking enabled.
- **Grounding metadata is best-effort.** Extract citations defensively; a
  restructured grounding block should cost you the citations, never the answer.

---

## 2. Config — three layers, one allow-list — `canon`

```
config/<app>_config.yml         committed, hand-authored, comments preserved,
                                NEVER machine-written
  → config/<app>_config.local.yml   git-ignored, written by the Config tab
    → UPPER_CASE environment variables       (highest precedence)
```

Merge is overlay, not in-place rewrite — so UI writes can never destroy the
documented defaults or their comments. The overlay carries an
`AUTO-GENERATED — do not hand-edit` header.

- **`EDITABLE_KEYS` is the API contract in both directions.** `GET` returns
  exactly those keys; `PATCH` rejects anything else with a
  `ValueError` → **HTTP 422**. Fail loud.
- YAML is `UPPER_CASE`, Python attributes are `snake_case`, one mechanical
  mapping into a Pydantic `Settings(extra="ignore")`.
- `get_settings()` is `lru_cache`d; the writer clears the cache and **returns
  the fresh state**, so the PATCH response *is* the new config and the client
  never refetches.
- **One shared `load_secrets()`** with an optional `path` argument — the
  argument exists so each caller keeps a patchable seam for tests.
  > Consolidating this without the seam once leaked the real `.secrets/.env`
  > into the test suite and broke client isolation.

---

## 3. Plug-and-play features — `canon`

Every optional capability is a directory under `src/features/<name>/` with a
`manifest.py`:

```python
MANIFEST = {
    "name": "ask_ai",
    "requires": ["api_key"],       # api_key | live_data | network | broker
    "routers": [ask.router],
    "static": ["js/ask_ai.js"],
    "config_keys": ["LLM_PROVIDER", "ASK_FOLLOWUPS_MAX"],
    "strip_in_export": True,
}
```

A registry discovers manifests, mounts what meets its requirements, and
reports the rest as **unavailable-with-reason** rather than crashing. Adding a
feature is dropping in a folder; removing it is deleting one.

> **`anti`: top-level imports of optional features.** One project's `app.py`
> did a bare `from src.dashboard.llm_query import …` at line 33, so the entire
> trading dashboard would not start without the `anthropic` package installed.
> Every optional module was cleanly isolated in `src/` and then re-entangled at
> the single import site.

> **`anti`: the frontend monolith.** Backends here are well-factored while
> their frontends reached 5,370 lines (`app.py`), 120 KB (`app.js`) and 103 KB
> (`deck.js`). At that size nothing can be excised, so plug-and-play dies at
> the UI layer even when the backend is perfect. **Hard cap: 400 lines per
> frontend module, one module per feature.**

---

## 4. Domain core — `canon`

`src/domain/` holds pure functions: DataFrames in, DataFrames out. It may not
import the web framework, the broker SDK, or anything under `features/`.

Every business rule gets a named test that encodes the rule as a worked
example. This is the only mechanism that reliably carries domain knowledge
across a rewrite — prose in a CLAUDE.md does not survive, a failing test does.

---

## 5. Routers by side-effect class — `canon`

`read.py` (pure reads) · `actions.py` (writes) · `auth.py` · `ask.py` (LLM
only). An auditor can then see at a glance what talks to an LLM, and what can
move money, without reading the implementation.

> **`anti`:** a read-only Q&A handler parked in the write router because that
> file already had the imports.

---

## 6. Redact at the data layer — `canon`

Sensitive material is dropped **at parse time**, so it never enters the DOM,
the payload, or the export bytes. Never hide with CSS, never filter in the
template — both survive "view source".

- The un-redacted path is behind an explicit flag that **prints a warning and
  renames the output file** (`-internal` suffix).
- Make the safe direction structural: the overlay/config layer can *set*
  redaction but has **no mechanism to clear it**. Pin it with tests from both
  directions.
- Defense in depth for LLM output: filter source chunks *before* scoring (so a
  redacted chunk cannot displace a usable one), instruct the model in the
  system prompt, and drop any suggestion chip containing a redacted term.

---

## 7. Standalone export — `canon`

One self-contained offline HTML: read-only payloads baked into
`window.__DATA__`, a `fetch` shim resolving `GET /api/...` from it (writes
become no-ops) so the app's own JS runs **unmodified**, CSS/JS/vendor inlined,
images as `data:` URIs swapped in by a `MutationObserver` (catches
`innerHTML`-built images). Collect payloads through an in-process test client
so the snapshot is byte-identical to live.

- Features with `strip_in_export` are removed, not hidden.
- Server-only controls are hidden by an injected bootstrap stylesheet, never by
  editing the app's JS.
- **Demo URLs degrade gracefully**: an unset, unreachable or stripped
  `live_url` renders as a disabled chip with a tooltip — never a dead link, a
  404, or a console error.
- **Lint for comment leakage.** The exporter inlines source comments verbatim;
  internal `spec.md` / "Feature N" language has twice leaked into client-facing
  view-source. Make it a check, not vigilance.

---

## 8. Feature IDs and the generated index — `canon`

**IDs are immutable and append-only.** Never renumber to make things sort —
renumbering breaks every commit message, PROGRESS entry and cross-reference
that referenced the old number.

Sorting is a **generated view**, not a file property. `scripts/index_docs.py`
regenerates a table between `<!-- FEATURE-INDEX:START -->` markers at the top
of `spec.md`, with columns: **ID · Title · Status · Logged · Commit**, where
status is `active` / `superseded` / `dropped`.

- Nothing is ever deleted from spec.md; it is marked `superseded` with a
  pointer to the feature that replaced it.
- The generator cross-checks spec against PROGRESS and flags both directions
  (specced-not-logged, logged-not-specced). Real drift it has caught: two
  features shipped and committed with no spec section at all.
- `BACKLOG.md` is the fourth state file: deferred work, **ordered by risk, not
  by feature number**, so "deferred" never quietly becomes "forgotten".

---

## 9. Brand — `canon`

See `templates/.claude/skills/brand-visuals/SKILL.md`. The load-bearing rules:
RKV is the seed and a client skin is an explicit override; colors are always
semantic CSS variables; **no `var(--x, #hex)` fallbacks**; ship both
`prefers-color-scheme` and a `data-theme` toggle; sharp geometry, no gradients,
no shadows.

Chart libraries are the usual leak — their default palettes and hoverlabel
colors are hardcoded hex that ignores your theme. Override them with tokens.

---

## 10. Operational hygiene — `canon`

- **Merge, never replace, on-disk data.** No bare `to_pickle()` over an
  existing store.
- **Scaffolding must fail loud on placeholders.** `new-project` aborts if any
  `{{...}}` or `__YOUR_...__` token survives. Three live projects shipped with
  `__YOUR_LINTER__` still in their permission allow-lists, so `ruff` and
  `pytest` were never actually allowlisted and prompted on every call for
  weeks.
- **Auto-commit hooks must not spam history.** A Stop hook producing
  `wip: auto-checkpoint` at 7–9 of every 15 commits makes `git log` useless as
  an index. Amend a single rolling checkpoint instead of appending.
- **Never let a doc claim a capability the code lost.** A skill advertising
  `prefers-color-scheme` while the shipped stylesheet dropped it is worse than
  no doc — it stops people checking.
