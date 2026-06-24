#!/usr/bin/env bash
# post_edit_stage.sh
# Fires on PostToolUse for Edit/Write tools.
# Purpose: keep git index current with zero token cost, and run ruff
# auto-fix + format on any touched Python file so style never drifts.
#
# Reads the tool input JSON from stdin (Claude Code convention).

set -euo pipefail
cd "$CLAUDE_PROJECT_DIR"

LOG_FILE=".claude/hooks.log"
TS="$(date '+%Y-%m-%d %H:%M:%S')"

INPUT_JSON="$(cat)"

# Extract file_path from the tool input (works for Edit/Write tool schemas)
FILE_PATH="$(echo "$INPUT_JSON" | grep -o '"file_path"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed -E 's/.*"file_path"[[:space:]]*:[[:space:]]*"([^"]*)"/\1/' || true)"

if [ -z "${FILE_PATH:-}" ]; then
  exit 0
fi

# Only act on files inside the project, ignore data/ and .venv/
case "$FILE_PATH" in
  *"/data/"*|*"/.venv/"*|*"/.git/"*)
    exit 0
    ;;
esac

# If it's a source file, run the configured linter/formatter silently.
# Set LINTER_FIX and LINTER_FORMAT to your tool's commands, or leave blank to skip.
# Examples:
#   Python (ruff): LINTER_FIX="ruff check --fix --quiet"  LINTER_FORMAT="ruff format --quiet"
#   JS (biome):    LINTER_FIX="biome check --apply"        LINTER_FORMAT=""
LINTER_FIX="__YOUR_LINT_FIX_CMD__"      # e.g. ruff check --fix --quiet
LINTER_FORMAT="__YOUR_FORMAT_CMD__"     # e.g. ruff format --quiet

if [ -f "$FILE_PATH" ]; then
  case "$LINTER_FIX" in
    __YOUR_*|"") : ;;  # placeholder not filled in / disabled — skip
    *)
      FIRST_WORD="${LINTER_FIX%% *}"
      if command -v "$FIRST_WORD" >/dev/null 2>&1; then
        $LINTER_FIX "$FILE_PATH" 2>>"$LOG_FILE" || true
        [ -n "$LINTER_FORMAT" ] && case "$LINTER_FORMAT" in __YOUR_*) : ;; *) $LINTER_FORMAT "$FILE_PATH" 2>>"$LOG_FILE" || true ;; esac
      fi
      ;;
  esac
fi

# Stage the file if we're in a git repo
if [ -d .git ]; then
  git add -- "$FILE_PATH" 2>>"$LOG_FILE" || true
fi

echo "[$TS] post_edit_stage: processed $FILE_PATH" >> "$LOG_FILE"
exit 0
