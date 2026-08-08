"""Dashboard launch plumbing: which port, which browser.

Two problems this solves for every workspace dashboard.

**Browser** — `webbrowser.open()` hands the URL to the Windows default
handler, which errors on a cold launch when the default is a Chromium fork
(Thorium, in this workspace). So the exe is launched *directly* with the URL
as an argument, which does not hit that failure: `DASH_BROWSER` if set, else
the first of Thorium / Brave / Chrome / Edge / Opera actually installed, and
only then the OS default. Thorium leads because it is the user's daily browser — the
workspace browser rule is that terminal-driven `uv run` opens there, while
Claude's test instances use `DASH_BROWSER=chrome` with `?test=TestN-<app>` in
the URL (the app sets the tab title from it) and are closed after testing.
Opening the browser must never take the server down, so every failure here
degrades to "print the URL".

**Port** — each app owns one port from the workspace registry (`PORTS.md` at
the workspace root) and reads a per-app env var so a stale process squatting
the default never blocks a fresh start.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

# Preference order, first installed wins. Thorium leads: it is the user's
# daily browser, and the historical failure ("errors on a cold URL launch")
# was specific to handing the URL to the *Windows default handler* — launching
# the exe directly with the URL as an argument does not hit it. The browser
# rule (workspace CLAUDE.md): terminal-driven `uv run` opens Thorium; Chrome
# is reserved for Claude's test instances (`DASH_BROWSER=chrome`,
# `?test=TestN-<app>` in the URL so the tab is identifiable and closable).
_BROWSERS: dict[str, tuple[str, ...]] = {
    "thorium": (
        r"~\AppData\Local\Thorium\Application\thorium.exe",
        r"C:\Program Files\Thorium\Application\thorium.exe",
        "thorium",
    ),
    "brave": (
        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"~\AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe",
        "brave-browser",
        "brave",
    ),
    "chrome": (
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"~\AppData\Local\Google\Chrome\Application\chrome.exe",
        "google-chrome",
        "chrome",
    ),
    "edge": (
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        "msedge",
    ),
    "opera": (
        r"~\AppData\Local\Programs\Opera\opera.exe",
        r"C:\Program Files\Opera\opera.exe",
        r"C:\Program Files (x86)\Opera\opera.exe",
        "opera",
    ),
}

_PREFERENCE = ("thorium", "brave", "chrome", "edge", "opera")


def _resolve(candidate: str) -> str | None:
    """An installed executable path for `candidate` (a browser name, a bare
    command, or an explicit path), or None."""
    for path in _BROWSERS.get(candidate.lower(), (candidate,)):
        expanded = Path(path).expanduser()
        if expanded.is_file():
            return str(expanded)
        found = shutil.which(str(path))
        if found:
            return found
    return None


# "Don't open anything." Distinct from `default` (which means "let the OS
# handle it") and from an unresolvable value (which falls back). It exists
# because there was no way to say it: `DASH_BROWSER=none` was treated as a
# browser NAME, failed to resolve, and fell back through the preference order
# into Thorium — opening the user's daily browser from an automated test run,
# which is the one thing the browser rule forbids.
_SUPPRESS = {"none", "off", "no", "0", "false"}


def browser_suppressed() -> bool:
    return os.environ.get("DASH_BROWSER", "").strip().lower() in _SUPPRESS


def find_browser() -> tuple[str, str] | None:
    """`(name, exe_path)` of the browser to use, or None to mean "no known
    browser installed — let the OS default handle it". `DASH_BROWSER` (a name
    like `chrome` or a full .exe path) overrides the preference order; setting
    it to `default` opts back into `webbrowser.open`."""
    override = os.environ.get("DASH_BROWSER", "").strip()
    if override:
        if override.lower() == "default":
            return None
        exe = _resolve(override)
        if exe:
            return override, exe
        print(f"[launcher] DASH_BROWSER={override!r} not found, falling back", file=sys.stderr)
    for name in _PREFERENCE:
        exe = _resolve(name)
        if exe:
            return name, exe
    return None


def open_url(url: str) -> None:
    """Open `url`, preferring a known-good browser. Never raises — a browser
    that refuses to start must not stop the server that already bound the
    port; the URL is printed so the user can click it themselves."""
    if browser_suppressed():
        print(f"[launcher] browser suppressed (DASH_BROWSER) — open {url} yourself")
        return
    choice = find_browser()
    if choice is not None:
        name, exe = choice
        try:
            subprocess.Popen(  # noqa: S603 - exe resolved from a fixed allowlist above
                [exe, url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
            )
            print(f"[launcher] opened {url} in {name}")
            return
        except OSError as exc:
            print(f"[launcher] {name} failed to launch ({exc}), trying OS default", file=sys.stderr)
    try:
        webbrowser.open(url)
    except Exception as exc:  # noqa: BLE001 - platform handlers raise anything
        print(f"[launcher] could not open a browser ({exc})", file=sys.stderr)
    print(f"[launcher] dashboard at {url}")


def open_url_soon(url: str, delay: float = 1.5) -> None:
    """Open `url` on a daemon thread once the server has had time to bind."""

    def _run() -> None:
        time.sleep(delay)
        open_url(url)

    threading.Thread(target=_run, daemon=True).start()


def resolve_port(env_var: str, default: int) -> int:
    """This app's port: `$env_var` when set and numeric, else its registry
    default (see PORTS.md at the workspace root). A non-numeric value is a
    typo worth failing on, not worth silently ignoring."""
    raw = os.environ.get(env_var, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{env_var}={raw!r} is not a port number") from exc
