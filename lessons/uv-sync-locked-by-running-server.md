---
name: uv-sync-locked-by-running-server
description: "uv add/sync fails with \"Access denied ... Scripts/insead.exe\" whenever an insead server is still running; stop it first (POST /api/shutdown or taskkill)"
metadata: 
  node_type: memory
  type: project
  originSessionId: 59e60d66-1e7f-44cc-810c-23b8e46b8d07
---

On Windows, `uv add` / `uv sync` in the insead project fails with
`error: failed to remove file ... Scripts/insead.exe: Access is denied (os
error 5)` — and silently rolls back the pyproject change — whenever a
`uv run insead` server (or `insead ask`) is still running, because the
running process locks the console-script exe. Seen 2026-07-05: the user had
left the brochure server up.

**Why:** editable-install re-link happens on every sync; Windows cannot
replace a locked exe.

**How to apply:** before any dependency change, check `netstat -ano | grep
:8000`; stop the server gracefully via the brochure's Shutdown button /
`POST /api/shutdown` (Feature 11), else `taskkill //PID <pid> //F`, then
re-run the `uv` command and verify pyproject actually gained the deps.
