# rkv-ask — canonical Ask AI dock + provider layer

Extracted from `tatasons` (frontend) and `kite` (backend — the small
bottom-left dock with upward expansion, currently the cleanest live
implementation) and generalized. See `PATTERNS.md` §1.

**Copy all three files in, don't rebuild from memory:**
- `ask.css` + `ask.js` → the project's `static/`, then map the tokens (§1).
- `llm_client.py` → the project's `src/core/` (or `src/features/ask_ai/` if
  the project uses the plug-and-play layout), rename `<PROJECT>` references,
  prune to the providers actually needed.

**If this folder is vendored into a repo (e.g. `static/vendor/rkv-ask/`),
the feature's boot code must mount `#askDock` — a hand-built panel bolted
onto a tab instead is a second, divergent UI, and the vendored copy sitting
next to it unused is the tell.** This has already happened once: a project
copied this directory in, then wrote its own inline question/answer panel
from scratch anyway, producing a different UX from every other project and
re-deciding (worse) answers to problems this dock had already solved
(thread persistence across re-renders, markdown escaping, error bubbles that
keep the thread alive). Grep for `#askDock` before writing any Ask AI
frontend code — if this directory exists in the repo, wiring into it is not
optional.

The same applies to the backend: `llm_client.py` encodes two mistakes that
have each cost debugging time on **two separate projects** so far because
the second build didn't copy this file — see its module docstring (the
Anthropic zero-balance trap, and the correct Gemini SDK package name). Start
from it; don't reconstruct the provider registry from prose memory.

## Why a dock and not a bar

The dock mounts on `<body>`, so its thread and input **survive the host app's
re-renders**. Ask panels welded into a page region get wiped whenever that
region re-renders, which is why earlier versions lost the conversation on every
tab switch.

## 1. Map the tokens (once per project)

`ask.css` references only `--ask-*`, so it drops into any palette. Add this to
the project's own stylesheet, pointing at whatever its tokens are called:

```css
:root {
  --ask-accent:        var(--brand-primary);   /* fab, send, active pill, focus */
  --ask-accent-text:   #ffffff;                /* text ON accent */
  --ask-surface:       var(--card);            /* panel, buttons, chips */
  --ask-surface-alt:   var(--bg);              /* bot bubble, input field */
  --ask-text:          var(--ink);
  --ask-body:          var(--ink);             /* answer text */
  --ask-muted:         var(--muted);
  --ask-link:          var(--brand-secondary);
  --ask-border:        var(--line);            /* internal dividers */
  --ask-border-strong: var(--line);            /* panel + control outlines */
  --ask-hl:            var(--chip);            /* error bg, inline code bg */
  --ask-warn:          var(--hot);             /* error text */
  --ask-shadow:        rgba(0,0,0,.14);
  --ask-panel-shadow:  rgba(0,0,0,.20);
}
[data-theme="dark"] { /* re-map only what must change */ }
```

No `var(--x, #hex)` fallbacks. A missing token is a bug in the mapping.

## 2. Configure the front end

Define `window.ASK_CONFIG` **before** loading `ask.js`:

```html
<script>
  window.ASK_CONFIG = {
    endpoint: '/api/ask',
    configUrl: '/api/config',
    testUrl: '/api/ask/test',        // omit if not implemented
    providers: ['gemini', 'deepseek', 'claude'],
    emptyText: 'Ask anything about …',
    showWebToggle: true,             // false where no web search exists
    defaultContext: () => ({ entity_type: 'market', entity_id: null }),
    themeOf: () => document.documentElement.dataset.theme || 'light',
  };
</script>
<script src="/static/js/ask.js?v=1"></script>
```

Open it grounded on one entity from anywhere in the host app:

```js
askOpenFor({ entity_type: 'company', entity_id: id, label: name });
```

The context renders as a dismissible chip in the controls row, so the user can
always see — and clear — what the answer is grounded on. **Never ground
silently**; an invisible context is a stale-context bug waiting to happen.

## 3. Backend contract

**Provider layer**: `llm_client.py` in this folder — `get_client(name)` and
`provider_status()` back the two endpoints below. Don't reimplement the
registry, retry, or model-pinning; copy the file and prune providers.

**The two-endpoint rule** (PATTERNS.md §1a) — "a key is present" and "the key
works" are different claims:

```python
@router.get("/providers")
def providers() -> dict:
    """Free, local, no provider contacted. Backs the Config panel's poll."""
    return {"providers": provider_status(), "default": DEFAULT_PROVIDER}


@router.post("/test")
def test_provider(body: TestRequest | None = None) -> dict:
    """One real round-trip. NEVER raises — every failure path, including a
    bare Exception, returns {provider, ok: false, detail}. This is what
    catches a key that is present, valid, and out of credit."""
    name = (body.provider if body else None) or DEFAULT_PROVIDER
    try:
        client = get_client(name)
        answer = client.ask("Answer with one word.", "Reply with: OK")
    except Exception as exc:  # noqa: BLE001 - by design, see docstring
        return {"provider": name, "ok": False, "detail": str(exc)}
    return {"provider": name, "ok": True, "model_id": answer.model_id,
            "reply": answer.text.strip()[:80]}
```

`AskResponse` must carry `suggestions`. The chips are produced by asking the
model for a JSON tail and splitting it off — no second call, no extra cost:

```python
SUGGESTION_MARKER = "SUGGESTIONS:"
_MAX_SUGGESTIONS = 5

_SUGGESTION_CONTRACT = (
    "After your answer, on a NEW FINAL LINE, output exactly:\n"
    f'{SUGGESTION_MARKER} ["q1", "q2", "q3", "q4", "q5"]\n'
    "— a JSON array of exactly 5 short, specific follow-up questions the user "
    "might ask next. Output nothing after that line.\n\n"
)


def parse_suggestions(raw: str) -> tuple[str, list[str]]:
    """Split the answer from its trailing JSON suggestion array."""
    idx = raw.rfind(SUGGESTION_MARKER)          # rfind: a marker mentioned
    if idx == -1:                               # mid-answer must not truncate
        return raw.strip(), []
    answer = raw[: idx].strip()
    tail = raw[idx + len(SUGGESTION_MARKER) :].strip()
    suggestions: list[str] = []
    match = re.search(r"\[.*\]", tail, re.DOTALL)   # DOTALL: multi-line arrays
    if match:
        try:
            parsed = json.loads(match.group(0))
            if isinstance(parsed, list):
                suggestions = [
                    str(s).strip() for s in parsed if str(s).strip()
                ][:_MAX_SUGGESTIONS]
        except (ValueError, TypeError):
            suggestions = []
    # If the model put everything after the marker, never return a blank reply.
    return (answer or raw.strip()), suggestions
```

Three caps in series, deliberately: the model is asked for 5, the server clamps
to 5, the client displays 2. Generating more than are shown is not waste — it
lets the client widen the row without a round-trip, and the surplus is the
cheapest part of the response.

If the project redacts terms (PATTERNS.md §6), filter the suggestions too — a
chip must never surface what the answer is forbidden to say.

## 4. Two caps, never conflated

| Cap | Meaning | Where |
|---|---|---|
| `maxFollowups` (5) | how many turns the user may take | client budget |
| `history[-8:]` | how much thread reaches the model | server |
| `visibleChips` (2) | how many suggestion chips render | client |

An error does **not** decrement the follow-up budget — a retry is free.

## 5. States the panel must handle

Closed (fab only) · empty (centred prompt copy) · in-flight (`pending` bubble,
input disabled) · error (bubble carrying the server's `detail` verbatim, thread
stays alive) · long answer (only `.ask-thread` scrolls, auto-pinned to bottom,
per-answer copy button) · exhausted (notice + disabled input + Reset).

## 6. Do not rename the classes

`export_static.py` hides the dock by CSS selector (`#askDock`). Renaming a class
silently leaks a server-dependent UI into an offline client handout — a bug that
has already shipped once.
