#!/usr/bin/env bash
# stop_autocommit.sh
# Fires on Stop (end of Claude's turn).
# Purpose: if there's uncommitted work staged by post_edit_stage.sh, commit it
# with a generic WIP message so a session crash never loses work outright.
# This is a SAFETY NET, not a substitute for proper feature commits —
# Claude should still be making clean, descriptive commits per the CLAUDE.md workflow.

set -euo pipefail
cd "$CLAUDE_PROJECT_DIR"

LOG_FILE=".claude/hooks.log"
TS="$(date '+%Y-%m-%d %H:%M:%S')"

if [ ! -d .git ]; then
  exit 0
fi

if ! git diff --cached --quiet 2>/dev/null; then
  git commit -m "wip: auto-checkpoint $TS" --quiet || true
  echo "[$TS] Stop hook: committed staged WIP." >> "$LOG_FILE"
elif ! git diff --quiet 2>/dev/null; then
  # unstaged changes exist but weren't caught by post_edit_stage — stage + commit anyway
  git add -A
  git commit -m "wip: auto-checkpoint (unstaged) $TS" --quiet || true
  echo "[$TS] Stop hook: staged + committed unstaged WIP." >> "$LOG_FILE"
fi

exit 0
