"""Dashboard launch plumbing: which port, which browser.

Two problems this solves for every workspace dashboard.

**Browser** — `webbrowser.open()` hands the URL to the Windows default handler.
When that default is a Chromium fork that errors on a cold `--new-tab` launch
(Thorium, in this workspace), the dashboard starts fine but the window never
appears. So we pick an explicitly-known-good browser instead: `DASH_BROWSER`
if set, else the first of Brave / Chrome / Edge actually installed, and only
then fall back to the OS default. Opening the browser must never take the
server down, so every failure here degrades to "print the URL".

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

# Preference order, first installed wins. Deliberately excludes Thorium: it is
# the machine default and the one that fails to launch from a cold URL open.
_BROWSERS: dict[str, tuple[str, ...]] = {
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
}

_PREFERENCE = ("brave", "chrome", "edge")


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
