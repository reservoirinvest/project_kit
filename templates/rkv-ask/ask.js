/* ===========================================================================
 * rkv-ask — canonical Ask AI dock.
 * Extracted from tatasons (the reference implementation) and generalized.
 *
 * Mounted on <body> so the thread and input survive the host app's re-renders.
 * Self-contained: own state, own DOM, no framework, no build step.
 *
 * CONFIGURE by defining window.ASK_CONFIG *before* loading this file:
 *
 *   window.ASK_CONFIG = {
 *     endpoint:   '/api/ask',           // POST target
 *     configUrl:  '/api/config',        // GET/PATCH provider
 *     testUrl:    '/api/ask/test',      // optional: provider round-trip test
 *     providers:  ['gemini', 'deepseek', 'claude'],
 *     labels:     { gemini: 'Gemini', deepseek: 'DeepSeek', claude: 'Claude' },
 *     emptyText:  'Ask anything about …',
 *     showWebToggle: true,              // false where no web search exists
 *     maxFollowups:  5,
 *     visibleChips:  2,                 // of up to 5 generated
 *     // Optional: what the dock is grounded on. Return null for global scope.
 *     defaultContext: () => ({ entity_type: 'market', entity_id: null }),
 *     themeOf:    () => document.documentElement.dataset.theme || 'light',
 *   };
 *
 * Open it grounded on a specific entity from anywhere in the host app:
 *
 *   askOpenFor({ entity_type: 'company', entity_id: id, label: name });
 *
 * INVARIANTS (see PATTERNS.md §1) — changing these breaks the pattern:
 *   - one state object, full innerHTML re-render, re-bind after every render
 *   - data-ask-* attribute wiring, every handler stopPropagation()
 *   - escape-then-re-introduce markdown (never innerHTML raw model output)
 *   - "pending" is a real message, not a separate spinner state
 *   - an error is a bubble and does NOT cost a follow-up
 * ======================================================================== */

const ASK_CFG = Object.assign(
  {
    endpoint: '/api/ask',
    configUrl: '/api/config',
    testUrl: null,
    providers: ['gemini', 'deepseek', 'claude'],
    labels: { gemini: 'Gemini', deepseek: 'DeepSeek', claude: 'Claude' },
    emptyText: 'Ask a question. Answers are grounded in this app’s data.',
    showWebToggle: true,
    maxFollowups: 5,
    visibleChips: 2,
    defaultContext: () => null,
    themeOf: () => document.documentElement.dataset.theme || 'light',
  },
  window.ASK_CONFIG || {},
);

const ask = {
  open: false,
  web: false,
  started: false,
  left: ASK_CFG.maxFollowups,
  provider: ASK_CFG.providers[0],
  messages: [],
  suggestions: [],
  busy: false,
  copiedIdx: new Set(),
  ctx: null, // {entity_type, entity_id, label} or null for the default scope
  test: null, // {ok, detail} from the last provider test
};
let askDock = null;

/* ---- escaping + minimal markdown --------------------------------------- */
function askEsc(s) {
  return String(s).replace(
    /[&<>"']/g,
    (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]),
  );
}

function askMdInline(s) {
  return s
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/(^|[^*])\*([^*\s][^*]*?)\*/g, '$1<em>$2</em>');
}

function askMd(text) {
  const lines = askEsc(text).split('\n');
  let html = '';
  let inList = false;
  const closeList = () => { if (inList) { html += '</ul>'; inList = false; } };
  for (const raw of lines) {
    const line = raw.replace(/\r$/, '');
    const bullet = line.match(/^\s*[-*]\s+(.*)$/);
    const numbered = line.match(/^\s*\d+\.\s+(.*)$/);
    const head = line.match(/^\s*(#{1,3})\s+(.*)$/);
    if (bullet || numbered) {
      if (!inList) { html += '<ul>'; inList = true; }
      html += '<li>' + askMdInline((bullet || numbered)[1]) + '</li>';
    } else if (head) {
      closeList();
      html += '<div class="md-h">' + askMdInline(head[2]) + '</div>';
    } else if (line.trim() === '') {
      closeList();
    } else {
      closeList();
      html += '<p>' + askMdInline(line) + '</p>';
    }
  }
  closeList();
  return html || '<p></p>';
}

function askProviderLabel(p) { return ASK_CFG.labels[p] || p; }

/* ---- render ------------------------------------------------------------ */
function renderAsk() {
  if (!askDock) return;

  if (!ask.open) {
    askDock.innerHTML =
      '<button class="ask-fab" data-ask-open><span class="ask-spark">✦</span>Ask AI</button>';
    askBind();
    return;
  }

  const exhausted = ask.started && ask.left <= 0;
  const counter = !ask.started
    ? `${ASK_CFG.maxFollowups} follow-ups after your first question`
    : exhausted
      ? 'Follow-up limit reached'
      : `${ask.left} follow-up${ask.left !== 1 ? 's' : ''} left`;

  const providerOpts = ASK_CFG.providers
    .map((p) => `<option value="${p}"${p === ask.provider ? ' selected' : ''}>${askProviderLabel(p)}</option>`)
    .join('');

  const testBtn = ASK_CFG.testUrl
    ? `<button class="ask-test${ask.test ? (ask.test.ok ? ' ok' : ' bad') : ''}" data-ask-test
         title="${ask.test ? askEsc(ask.test.detail) : 'Test this provider'}"
         aria-label="Test provider">${ask.test ? (ask.test.ok ? '✓' : '✗') : '◎'}</button>`
    : '';

  let thread = '';
  if (!ask.messages.length) {
    thread = `<div class="ask-empty">${askEsc(ASK_CFG.emptyText)}</div>`;
  } else {
    ask.messages.forEach((m, i) => {
      if (m.role === 'user') {
        thread += `<div class="ask-bubble user">${askEsc(m.content)}</div>`;
      } else if (m.role === 'pending') {
        thread += '<div class="ask-bubble pending">Thinking…</div>';
      } else if (m.role === 'error') {
        thread += `<div class="ask-bubble err">${askEsc(m.content)}</div>`;
      } else {
        // data-ask-copy carries the message INDEX, not the text — so the copy
        // is the exact source string, not an HTML-attribute-normalized one.
        const copied = ask.copiedIdx.has(i);
        thread += `<div class="ask-bubble bot"><div class="ask-md">${askMd(m.content)}</div>
          <div class="ask-bubble-foot">
            <button class="ask-copy${copied ? ' on' : ''}" data-ask-copy="${i}" title="Copy answer" aria-label="Copy answer to clipboard">${copied ? '✓' : '⧉'}</button>
            ${m.meta ? `<span class="ask-meta">${askEsc(m.meta)}</span>` : ''}
          </div>
        </div>`;
      }
    });
  }

  const chips = !ask.busy && ask.suggestions.length && !exhausted
    ? `<div class="ask-chips">${ask.suggestions
        .slice(0, ASK_CFG.visibleChips)
        .map((s) => `<button class="ask-chip" data-ask-chip="${askEsc(s)}">${askEsc(s)}</button>`)
        .join('')}</div>`
    : '';

  const ctxChip = ask.ctx && ask.ctx.label
    ? `<span class="ask-ctx">${askEsc(ask.ctx.label)}<button data-ask-ctx-clear title="Ask across everything instead" aria-label="Clear context">×</button></span>`
    : '';

  const webToggle = ASK_CFG.showWebToggle
    ? `<span class="ask-modes">
         <button class="ask-mode${!ask.web ? ' on' : ''}" data-ask-mode="grounded">Grounded</button>
         <button class="ask-mode${ask.web ? ' on' : ''}" data-ask-mode="web">+ Web</button>
       </span>`
    : '';

  const inputDisabled = ask.busy || exhausted;
  askDock.innerHTML = `<div class="ask-panel">
    <div class="ask-head">
      <span class="ask-title">✦ Ask AI</span>
      <select class="ask-model" data-ask-provider title="LLM provider">${providerOpts}</select>
      ${testBtn}
      <button class="ask-x" data-ask-close title="Close">×</button>
    </div>
    <div class="ask-controls">
      ${webToggle}
      ${ctxChip}
      <span class="ask-counter">${counter}</span>
      ${ask.messages.length ? '<button class="ask-reset" data-ask-reset>Reset</button>' : ''}
    </div>
    <div class="ask-thread" id="ask-thread">${thread}</div>
    ${chips}
    ${exhausted ? '<div class="ask-exhausted">Follow-up thread complete — <b>Reset</b> to start a new one.</div>' : ''}
    <div class="ask-input-row">
      <input class="ask-input" id="ask-input" type="text" placeholder="${exhausted ? 'Reset to ask again…' : 'Ask a question…'}" ${inputDisabled ? 'disabled' : ''}>
      <button class="ask-send" data-ask-send ${inputDisabled ? 'disabled' : ''}>Ask</button>
    </div>
  </div>`;

  askBind();
  const thr = document.getElementById('ask-thread');
  if (thr) thr.scrollTop = thr.scrollHeight;
  const inp = document.getElementById('ask-input');
  if (inp && !inputDisabled) inp.focus();
}

/* ---- wiring ------------------------------------------------------------ */
function askBind() {
  const q = (sel, fn, evt = 'click') =>
    askDock.querySelectorAll(sel).forEach((el) =>
      el.addEventListener(evt, (e) => { e.stopPropagation(); fn(el, e); }));

  q('[data-ask-open]', () => { ask.open = true; renderAsk(); });
  q('[data-ask-close]', () => { ask.open = false; renderAsk(); });
  q('[data-ask-reset]', () => askReset());
  q('[data-ask-mode]', (el) => { ask.web = el.dataset.askMode === 'web'; renderAsk(); });
  q('[data-ask-provider]', (el) => askSetProvider(el.value), 'change');
  q('[data-ask-send]', () => askSend());
  q('[data-ask-test]', () => askTestProvider());
  q('[data-ask-ctx-clear]', () => { ask.ctx = null; renderAsk(); });
  q('[data-ask-chip]', (el) => {
    const inp = document.getElementById('ask-input');
    if (inp) inp.value = el.dataset.askChip;
    askSend();
  });
  q('[data-ask-copy]', (el) => askCopy(Number(el.dataset.askCopy)));

  const inp = askDock.querySelector('#ask-input');
  if (inp) {
    inp.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') { e.preventDefault(); askSend(); }
    });
  }
}

/* ---- send -------------------------------------------------------------- */
async function askSend() {
  const inp = document.getElementById('ask-input');
  const prompt = inp && inp.value ? inp.value.trim() : '';
  if (!prompt || ask.busy) return;
  if (ask.started && ask.left <= 0) return;

  // History is built BEFORE the current prompt is pushed.
  const history = ask.messages
    .filter((m) => m.role === 'user' || m.role === 'bot')
    .map((m) => ({ role: m.role === 'bot' ? 'assistant' : 'user', content: m.content }));

  ask.messages.push({ role: 'user', content: prompt });
  ask.messages.push({ role: 'pending' });
  ask.suggestions = [];
  ask.busy = true;
  renderAsk();

  const ctx = ask.ctx || ASK_CFG.defaultContext() || {};
  const body = Object.assign({ prompt, history, use_web: ask.web }, {
    entity_type: ctx.entity_type,
    entity_id: ctx.entity_id,
  });
  Object.keys(body).forEach((k) => body[k] === undefined && delete body[k]);

  let res;
  try {
    const r = await fetch(ASK_CFG.endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    let data = null;
    try { data = await r.json(); } catch (_) { data = { detail: (await r.text()) || `HTTP ${r.status}` }; }
    res = { ok: r.ok, data };
  } catch (e) {
    res = { ok: false, data: { detail: e.message } };
  }

  ask.busy = false;
  ask.messages = ask.messages.filter((m) => m.role !== 'pending');

  if (res.ok) {
    ask.messages.push({
      role: 'bot',
      content: res.data.response,
      meta: `${res.data.model} · ${res.data.provider}${ask.web ? ' · web' : ''}`,
    });
    ask.suggestions = Array.isArray(res.data.suggestions) ? res.data.suggestions.slice(0, 5) : [];
    if (!ask.started) { ask.started = true; ask.left = ASK_CFG.maxFollowups; }
    else ask.left = Math.max(0, ask.left - 1);
  } else {
    // An error does NOT cost a follow-up — a retry is free.
    ask.messages.push({ role: 'error', content: (res.data && res.data.detail) || 'Request failed' });
  }
  renderAsk();
}

/* ---- actions ----------------------------------------------------------- */
async function askCopy(i) {
  const m = ask.messages[i];
  if (!m || m.role !== 'bot') return;
  if (!navigator.clipboard || !navigator.clipboard.writeText) {
    console.warn('Ask AI: Clipboard API unavailable (needs HTTPS or localhost) — copy skipped.');
    return;
  }
  try {
    await navigator.clipboard.writeText(m.content); // raw markdown, not rendered HTML
  } catch (e) {
    console.warn('Ask AI: clipboard write failed', e);
    return;
  }
  ask.copiedIdx.add(i);
  renderAsk();
  setTimeout(() => { ask.copiedIdx.delete(i); renderAsk(); }, 1500);
}

function askReset() {
  ask.messages = [];
  ask.suggestions = [];
  ask.started = false;
  ask.left = ASK_CFG.maxFollowups;
  ask.busy = false;
  ask.copiedIdx.clear();
  renderAsk();
}

async function askSetProvider(provider) {
  ask.provider = provider;
  ask.test = null;
  try {
    await fetch(ASK_CFG.configUrl, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider }),
    });
  } catch (e) { /* best-effort; the server re-reads config per call */ }
  renderAsk();
}

/* "A key is present" and "the key works" are different questions
   (PATTERNS.md §1a). This asks the second one. */
async function askTestProvider() {
  if (!ASK_CFG.testUrl) return;
  ask.test = { ok: false, detail: 'testing…' };
  renderAsk();
  try {
    const r = await fetch(ASK_CFG.testUrl, { method: 'POST' });
    const d = await r.json();
    ask.test = d.ok
      ? { ok: true, detail: `${d.model_id} replied: ${d.reply || 'OK'}` }
      : { ok: false, detail: d.detail || `HTTP ${r.status}` };
  } catch (e) {
    ask.test = { ok: false, detail: e.message };
  }
  renderAsk();
}

/* Open the dock grounded on a specific entity, from anywhere in the host app. */
function askOpenFor(ctx) {
  ask.ctx = ctx || null;
  ask.open = true;
  askReset();
}

/* ---- lifecycle --------------------------------------------------------- */
function syncAskTheme() {
  if (askDock) askDock.dataset.theme = ASK_CFG.themeOf();
}

async function askInit() {
  askDock = document.createElement('div');
  askDock.id = 'askDock';
  document.body.appendChild(askDock);
  syncAskTheme();
  try {
    const r = await fetch(ASK_CFG.configUrl);
    if (r.ok) {
      const cfg = await r.json();
      if (cfg.provider) ask.provider = cfg.provider;
    }
  } catch (e) { /* offline / not wired — the default provider stands */ }
  renderAsk();
}

window.addEventListener('keydown', (e) => {
  // Never steal keys while the user is typing in the dock.
  if (ask.open && askDock && askDock.contains(document.activeElement)) {
    if (e.key === 'Escape') { ask.open = false; renderAsk(); }
    return;
  }
  if (e.key === 'Escape' && ask.open) { ask.open = false; renderAsk(); }
});

document.addEventListener('DOMContentLoaded', askInit);
