#!/usr/bin/env bash
# session_start_brief.sh
# Fires on SessionStart.
# Purpose: print PLAN.md + last PROGRESS.md entry to stdout so Claude
# Code can fold it into context for free, instead of Claude spending
# a Read tool call figuring out "where was I."

set -euo pipefail
cd "$CLAUDE_PROJECT_DIR"

if [ -f PLAN.md ]; then
  echo "=== Current PLAN.md ==="
  cat PLAN.md
  echo ""
fi

if [ -f PROGRESS.md ]; then
  echo "=== Most recent PROGRESS.md entry ==="
  # last entry = content after the last '## ' heading
  awk '/^## /{p=$0; buf=""} {buf=buf"\n"$0} END{print buf}' PROGRESS.md | tail -40
  echo ""
fi

if [ -f spec.md ]; then
  echo "=== spec.md feature headings (for reference) ==="
  grep -E '^## Feature' spec.md || echo "(no features yet)"
fi

exit 0
