#!/usr/bin/env bash
# session_start_brief.sh
# Fires on SessionStart.
# Purpose: print PLAN.md + last PROGRESS.md entry to stdout so Claude
# Code can fold it into context for free, instead of Claude spending
# a Read tool call figuring out "where was I."

set -euo pipefail
cd "$CLAUDE_PROJECT_DIR"

# --- Unfilled scaffolding check -------------------------------------------
# Three live projects shipped with __YOUR_LINTER__ still in their permission
# allow-lists, so uv/ruff/pytest were never actually allowlisted and prompted
# on every call for weeks. Nag every session until the placeholders are gone.
PLACEHOLDERS="$(grep -rlE '\{\{[A-Z_]+\}\}|__YOUR_[A-Z_]+__' \
  --include='*.md' --include='*.json' --include='*.sh' --include='*.yml' \
  --exclude-dir=.git --exclude-dir=.venv --exclude-dir=node_modules \
  . 2>/dev/null | head -20 || true)"

if [ -n "$PLACEHOLDERS" ]; then
  echo "=== ⚠ UNFILLED TEMPLATE PLACEHOLDERS ==="
  echo "These files still contain {{...}} or __YOUR_...__ tokens:"
  echo "$PLACEHOLDERS" | sed 's/^/  /'
  echo ""
  echo "If .claude/settings.json is listed, this project's tool permissions are"
  echo "DEAD — every uv/ruff/pytest call prompts. Fix before other work."
  echo ""
fi

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
