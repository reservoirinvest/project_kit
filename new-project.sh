#!/usr/bin/env bash
# new-project.sh
# One-shot bootstrap for a new spec-driven Claude Code project.
# Usage (from inside a NEW empty folder):
#   bash /path/to/new-project.sh
#
# Mirrors new-project.ps1. Stages templates only; Claude does nothing until
# you paste STARTUP_PROMPT.md and approve — that's the permission gate.

set -euo pipefail
KIT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="$(pwd)"

# --- 1. Safety: only run in an (almost) empty folder ---
shopt -s nullglob dotglob
existing=( * )
shopt -u nullglob dotglob
if [ "${#existing[@]}" -gt 0 ]; then
  echo "Folder is not empty. Found: ${existing[*]}"
  read -r -p "Proceed anyway and copy templates in? (y/N) " ans
  [ "$ans" = "y" ] || { echo "Aborted."; exit 1; }
fi

# --- 2. Copy templates ---
echo "Copying project templates into $TARGET ..."
cp -r "$KIT_ROOT"/templates/. "$TARGET"/

# Folder stubs
for d in src tests data .raw; do
  mkdir -p "$d"
  [ -f "$d/.gitkeep" ] || touch "$d/.gitkeep"
done

# .secrets/.env holds real values (git-ignored); .env.example (copied from
# templates/ above) is the git-tracked reference collaborators copy from.
mkdir -p .secrets
if [ ! -f .secrets/.env ] && [ -f .env.example ]; then
  cp .env.example .secrets/.env
fi

# Make hook scripts executable
chmod +x .claude/hooks/*.sh 2>/dev/null || true

# --- 3. Hand off (permission-gated) ---
cat <<'EOF'

Templates staged. Nothing else has run.

NEXT STEPS:
  1. Fill in the {{PLACEHOLDERS}} in STARTUP_PROMPT.md (toolchain, OS, brand).
  2. Launch Claude Code:   claude
  3. Paste the contents of STARTUP_PROMPT.md as your first message.
     Claude will propose a plan and ASK before creating/initializing anything.

  (STARTUP_PROMPT.md is in this folder now.)
EOF
