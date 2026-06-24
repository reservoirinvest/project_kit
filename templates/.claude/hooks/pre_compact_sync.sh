#!/usr/bin/env bash
# pre_compact_sync.sh
# Fires on PreCompact (both manual /compact and auto-compact).
# Purpose: refuse to let compaction proceed silently if state files are stale,
# and snapshot a git commit so nothing is lost to context loss.
#
# Exit code 0  -> compaction proceeds
# Exit code 2  -> Claude Code surfaces stderr to Claude and BLOCKS compaction,
#                 forcing Claude to act before retrying.

set -euo pipefail
cd "$CLAUDE_PROJECT_DIR"

LOG_FILE=".claude/hooks.log"
TS="$(date '+%Y-%m-%d %H:%M:%S')"

echo "[$TS] PreCompact fired" >> "$LOG_FILE"

# --- 0. Emergency bypass — lets user escape the context-limit deadlock.
#        Create the flag with:  touch .claude/hooks/.compact_bypass
#        It is one-shot: deleted immediately after being honoured. ---
BYPASS_FLAG=".claude/hooks/.compact_bypass"
if [ -f "$BYPASS_FLAG" ]; then
  rm -f "$BYPASS_FLAG"
  echo "[$TS] BYPASS: .compact_bypass flag found — skipping sync check (one-shot)." >> "$LOG_FILE"
  exit 0
fi

# --- 1. Is this even a git repo yet? (first run on empty folder) ---
if [ ! -d .git ]; then
  echo "[$TS] No git repo yet — skipping sync check (expected on first run)." >> "$LOG_FILE"
  exit 0
fi

# --- 2. Check for uncommitted changes in tracked source ---
if ! git diff --quiet || ! git diff --cached --quiet; then
  HAS_UNCOMMITTED=1
else
  HAS_UNCOMMITTED=0
fi

# --- 3. Check whether PLAN.md / PROGRESS.md were touched since the last commit ---
STATE_FILES_CHANGED=0
if [ -f PLAN.md ] || [ -f PROGRESS.md ]; then
  if git diff --name-only HEAD 2>/dev/null | grep -qE '^(PLAN|PROGRESS)\.md$'; then
    STATE_FILES_CHANGED=1
  fi
fi

# --- 4. If there's uncommitted source work but state files were NOT updated, BLOCK ---
SRC_CHANGED=0
if git diff --name-only HEAD 2>/dev/null | grep -qE '^src/|^tests/'; then
  SRC_CHANGED=1
fi

if [ "$SRC_CHANGED" -eq 1 ] && [ "$STATE_FILES_CHANGED" -eq 0 ]; then
  echo "[$TS] BLOCKED: src/tests changed but PLAN.md/PROGRESS.md not updated." >> "$LOG_FILE"
  cat >&2 <<'EOF'
PreCompact check failed: source files have uncommitted changes but PLAN.md
and PROGRESS.md were not updated to reflect them.

Before compacting, you must:
1. Update PLAN.md — set current feature status (in-progress / done / blocked)
2. Append one paragraph to PROGRESS.md — what was built, files touched, deviations from spec.md
3. If a new architectural decision was made, add it to ARCHITECTURE.md
4. Commit everything: git add -A && git commit -m "feat: <summary>"

Then retry compaction.

EMERGENCY (context-limit deadlock): if you cannot continue due to context limits,
run this in a terminal, then /compact immediately:
  touch .claude/hooks/.compact_bypass
The bypass is one-shot and self-deletes after use.
EOF
  exit 2
fi

# --- 5. Auto-commit if state files ARE in sync but nothing committed yet ---
if [ "$HAS_UNCOMMITTED" -eq 1 ]; then
  git add -A
  git commit -m "checkpoint: pre-compact sync $TS" --quiet || true
  echo "[$TS] Auto-committed pre-compact checkpoint." >> "$LOG_FILE"
fi

echo "[$TS] PreCompact check passed." >> "$LOG_FILE"
exit 0
