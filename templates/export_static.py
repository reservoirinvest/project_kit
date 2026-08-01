#!/usr/bin/env python3
"""Build a single self-contained, read-only ``.html`` snapshot of the app.

KIT TEMPLATE — see PATTERNS.md §7 "Standalone export". Copy into
``src/utils/export_static.py`` and fill in the CONFIGURE block. Everything
below that block is the reusable technique and should not need editing.

The snapshot opens **offline from disk with no server**:

* every read-only API payload the front-end requests is baked into
  ``window.__DATA__``;
* a ``fetch`` shim resolves GET ``/api/...`` from it (writes become no-ops), so
  the app's own JS runs **completely unchanged** — this is the crux: never fork
  a "static build" of your front-end, it will rot;
* CSS/JS/vendor are inlined, and every image is baked as a ``data:`` URI and
  swapped in at runtime by a MutationObserver (which is what catches images the
  app builds via ``innerHTML`` — a plain build-time rewrite misses those);
* server-only UI is hidden by an injected stylesheet, never by editing the JS.

Payloads are collected through an **in-process TestClient**, so the snapshot is
byte-identical to what the live app serves. Re-running is idempotent.

Run::

    uv run <project> export-static      # or: python -m src.utils.export_static
"""

from __future__ import annotations

import base64
import json
import mimetypes
import re
import sys
from pathlib import Path

# ===========================================================================
# CONFIGURE — the only project-specific part
# ===========================================================================

_THIS = Path(__file__).resolve()
ROOT = _THIS.parents[2]  # …/src/utils/ -> project root
STATIC = ROOT / "static"
INDEX_HTML = ROOT / "index.html"
OUTPUT = ROOT / "output"  # generated artifacts (git-ignored)
SAMPLE_OUT = OUTPUT / "static-app.html"

#: GET endpoints the front-end requests on boot. Anything missing here returns
#: an empty object offline rather than crashing — but the panel will be blank,
#: so keep this list honest.
BOOT_URLS: list[str] = [
    "/api/config",
    # "/api/...",
]

#: Endpoints whose payloads drive per-item detail URLs, expanded below in
#: ``_expand_dynamic_urls``.
LIST_URLS: list[str] = []

#: CSS selectors for anything that cannot work without a server: Ask AI, edit
#: tabs, job triggers, shutdown. Hidden, not deleted — deleting means touching
#: the app's own markup.
SERVER_ONLY_SELECTORS = ".askbar-wrap,.tab-edit,.jobs-panel,[data-server-only]"

#: JS/CSS/vendor bundles to inline, in load order.
VENDOR_JS: list[str] = []  # e.g. ["chart.umd.min.js", "marked.min.js"]
APP_JS: list[str] = ["js/app.js"]
APP_CSS: list[str] = ["css/app.css"]
BRAND_CSS = "brand.css"  # inlined first so tokens exist before app.css


def _expand_dynamic_urls(data: dict[str, object], grab) -> None:
    """Derive per-item detail URLs from already-fetched list payloads.

    Example::

        for c in data.get("/api/companies") or []:
            grab(f"/api/companies/{c['id']}")
    """
    return


def _make_test_client():
    """Return a TestClient wired to read-only dependencies.

    Override the session/DB dependency here so the export can never mutate
    live state, and skip the lifespan (``TestClient(app)`` without ``with``)
    so schedulers and broker connections never start.
    """
    from fastapi.testclient import TestClient

    from src.core.app import create_app

    return TestClient(create_app())


# ===========================================================================
# Reusable technique — should not need editing
# ===========================================================================

sys.path.insert(0, str(ROOT))

_IMG_EXTS = {".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico"}


def _data_uri(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{b64}"


def _collect_assets() -> dict[str, str]:
    """Every image under ``static/img`` → ``/static/img/<rel>``: data-URI."""
    assets: dict[str, str] = {}
    img_dir = STATIC / "img"
    if not img_dir.is_dir():
        return assets
    for p in sorted(img_dir.rglob("*")):
        if p.is_file() and p.suffix.lower() in _IMG_EXTS:
            rel = p.relative_to(STATIC).as_posix()
            assets[f"/static/{rel}"] = _data_uri(p)
    return assets


def _inline_css(assets: dict[str, str]) -> str:
    """Concatenated CSS with any ``url(/static/...)`` rewritten to a data URI."""
    parts: list[str] = []
    for name in ([BRAND_CSS] if BRAND_CSS else []) + APP_CSS:
        f = STATIC / name
        if f.is_file():
            parts.append(f.read_text(encoding="utf-8"))
    css = "\n".join(parts)

    def repl(match: re.Match) -> str:
        raw = match.group(1).strip("'\"")
        return f"url({assets.get(raw, raw)})"

    return re.sub(r"url\(\s*([^)]+?)\s*\)", repl, css)


def _collect_payloads() -> dict[str, object]:
    client = _make_test_client()
    data: dict[str, object] = {}

    def grab(url: str) -> object | None:
        r = client.get(url)
        if r.status_code == 200:
            data[url] = r.json()
            return data[url]
        return None

    for url in BOOT_URLS:
        grab(url)
    _expand_dynamic_urls(data, grab)
    for url in LIST_URLS:
        grab(url)
    return data


_BOOTSTRAP_TMPL = r"""
(function () {
  // ---- offline fetch shim: serve baked GET /api/... from window.__DATA__ ----
  function makeRes(body, ok, status) {
    ok = ok !== false; status = status || (ok ? 200 : 500);
    return {
      ok: ok, status: status, statusText: ok ? "OK" : "Error",
      json: function () { return Promise.resolve(body); },
      text: function () { return Promise.resolve(JSON.stringify(body)); },
      headers: { get: function () { return null; } },
    };
  }
  var _fetch = window.fetch ? window.fetch.bind(window) : null;
  window.fetch = function (input, init) {
    var url = (typeof input === "string") ? input : (input && input.url) || "";
    var method = ((init && init.method) || "GET").toUpperCase();
    var key = url.replace(location.origin, "");
    if (method === "GET" && key.indexOf("/api/") === 0) {
      if (Object.prototype.hasOwnProperty.call(window.__DATA__, key))
        return Promise.resolve(makeRes(window.__DATA__[key]));
      return Promise.resolve(makeRes({}, true, 200)); // unbaked GET -> empty, no crash
    }
    if (method !== "GET") return Promise.resolve(makeRes({ status: "ok" })); // writes no-op
    if (_fetch) return _fetch(input, init);
    return Promise.resolve(makeRes({}, false, 404));
  };

  // ---- swap /static images -> data URIs ----
  function fixImg(img) {
    var s = img.getAttribute("src") || "";
    if (s.indexOf("/static/") === 0 && window.__ASSETS__[s]) img.src = window.__ASSETS__[s];
  }
  // ---- demo/live links degrade to a disabled chip, never a dead link ----
  function fixDeadLink(a) {
    a.removeAttribute("target");
    a.setAttribute("href", "#");
    a.setAttribute("aria-disabled", "true");
    a.classList.add("is-offline");
    if (!a.getAttribute("title"))
      a.setAttribute("title", "Live link unavailable in the offline snapshot");
    a.addEventListener("click", function (e) { e.preventDefault(); });
  }
  function sweep(root) {
    if (!root.querySelectorAll) return;
    root.querySelectorAll('img[src^="/static/"]').forEach(fixImg);
    root.querySelectorAll('a[data-live-url], a[href^="http://localhost"], a[href^="/"]')
        .forEach(fixDeadLink);
  }
  new MutationObserver(function (muts) {
    for (var i = 0; i < muts.length; i++) {
      var added = muts[i].addedNodes;
      for (var j = 0; j < added.length; j++) {
        var n = added[j];
        if (n.nodeType !== 1) continue;
        if (n.tagName === "IMG") fixImg(n);
        sweep(n);
      }
    }
  }).observe(document.documentElement, { childList: true, subtree: true });

  // ---- hide everything that needs the server ----
  var style = document.createElement("style");
  style.textContent =
    '__SERVER_ONLY__{display:none!important}' +
    'a.is-offline{opacity:.55;cursor:not-allowed;text-decoration:none}';
  (document.head || document.documentElement).appendChild(style);

  document.addEventListener("DOMContentLoaded", function () { sweep(document); });
})();
"""


def _js_safe(obj: object) -> str:
    # json.dumps doesn't escape "</" — inside a <script> block "</script>" would
    # end the element early (the HTML parser runs before the JS parser).
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def build() -> str:
    """Return the full self-contained app HTML as a string."""
    assets = _collect_assets()
    data = _collect_payloads()
    css = _inline_css(assets)

    html = INDEX_HTML.read_text(encoding="utf-8")

    # 1) stylesheet links -> one inlined <style>
    html = re.sub(r'<link[^>]+href="/static/[^"]+\.css[^"]*"[^>]*>', "", html)
    html = html.replace("</head>", f"<style>\n{css}\n</style>\n</head>", 1)

    # 2) external <script src="/static/..."> -> removed (inlined below)
    html = re.sub(r'<script[^>]+src="/static/[^"]*"[^>]*>\s*</script>\s*', "", html)

    # 3) static markup images -> data URIs (dynamic ones handled at runtime)
    html = re.sub(
        r'(src|href)="(/static/img/[^"]+)"',
        lambda m: f'{m.group(1)}="{assets.get(m.group(2), m.group(2))}"',
        html,
    )

    bootstrap = _BOOTSTRAP_TMPL.replace("__SERVER_ONLY__", SERVER_ONLY_SELECTORS)
    blobs = (
        "<script>\n"
        f"window.__DATA__ = {_js_safe(data)};\n"
        f"window.__ASSETS__ = {_js_safe(assets)};\n"
        "</script>\n"
        f"<script>{bootstrap}</script>\n"
    )
    # Data + shim must exist before the app's JS runs -> inject into <head>.
    html = html.replace("</head>", blobs + "</head>", 1)

    scripts = "".join(
        f"<script>{(STATIC / name).read_text(encoding='utf-8')}</script>\n"
        for name in (
            [f"vendor/{v}" for v in VENDOR_JS] + APP_JS
        )
        if (STATIC / name).is_file()
    )
    html = html.replace("</body>", scripts + "</body>", 1)

    return html


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    SAMPLE_OUT.write_text(build(), encoding="utf-8")
    print(f"Wrote {SAMPLE_OUT}  ({SAMPLE_OUT.stat().st_size / 1024:,.0f} KB)")


if __name__ == "__main__":
    main()
