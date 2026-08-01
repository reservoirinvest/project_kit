#!/usr/bin/env bash
# stop_autocommit.sh
# Fires on Stop (end of Claude's turn).
#
# Purpose: never lose work to a session crash. This is a SAFETY NET, not a
# substitute for proper feature commits — Claude still makes clean, descriptive
# commits per the CLAUDE.md workflow.
#
# Rolling checkpoint: if HEAD is already an auto-checkpoint that has not been
# pushed, this AMENDS it rather than stacking another commit. Appending made
# `git log` useless as an index — checkpoints were running 7-9 of every 15
# commits in some repos, burying the real feature commits.
#
# Amend safety: never amends a commit that is not an auto-checkpoint, and never
# amends one already contained in the upstream branch.

set -euo pipefail
cd "$CLAUDE_PROJECT_DIR"

LOG_FILE=".claude/hooks.log"
TS="$(date '+%Y-%m-%d %H:%M:%S')"
WIP_PREFIX="wip: auto-checkpoint"

if [ ! -d .git ]; then
  exit 0
fi

# Nothing to do if the tree is clean (staged and unstaged both empty).
if git diff --cached --quiet 2>/dev/null && git diff --quiet 2>/dev/null; then
  exit 0
fi

git add -A

# Can we roll the existing checkpoint forward instead of adding a new one?
can_amend() {
  # HEAD must exist and be an auto-checkpoint.
  local subject
  subject="$(git log -1 --format=%s 2>/dev/null)" || return 1
  case "$subject" in
    "$WIP_PREFIX"*) ;;
    *) return 1 ;;
  esac

  # Never rewrite something already pushed.
  local upstream
  if upstream="$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null)"; then
    if git merge-base --is-ancestor HEAD "$upstream" 2>/dev/null; then
      return 1
    fi
  fi
  return 0
}

if can_amend; then
  git commit --amend -m "$WIP_PREFIX $TS" --quiet || true
  echo "[$TS] Stop hook: rolled auto-checkpoint forward (amended)." >> "$LOG_FILE"
else
  git commit -m "$WIP_PREFIX $TS" --quiet || true
  echo "[$TS] Stop hook: new auto-checkpoint." >> "$LOG_FILE"
fi

exit 0
