---
name: backup
description: Back up a live project to G:\My Drive\_projects — copy only. Nothing is deleted, nothing is de-registered, the workspace copy is untouched. Includes .git and never blocks on uncommitted work.
---

# /backup — copy a live project to Drive

Sibling of `/retire`. Same copy engine (`_project_kit/lib/project-copy.ps1`),
opposite intent:

| | `/backup` | `/retire` |
|---|---|---|
| Workspace copy | **untouched** | deleted (separate, confirmed step) |
| Registries (CLAUDE.md, PORTS.md, sync-skills) | **untouched** | updated |
| `.git` | **copied** | excluded |
| Uncommitted / unpushed work | **warns, proceeds** | blocks |
| Re-runnable | **yes, routinely** | once |

`/backup <project>` — e.g. `/backup mktdb`. `/backup all` backs up every live
project. No argument: list the projects and ask.

The script does the copying: `_project_kit/backup-project.ps1`. **Never
hand-roll the copy** — it holds the exclusion list and the verification.

## Never read `.secrets`

`.secrets/` is copied because a backup must be restorable. It moves via
robocopy at the file level. Do not `Read`, `cat`, `Get-Content`, grep or
otherwise open anything under `.secrets/` at any point — not to verify, not to
summarise. `Test-Path` (which the script already does) is the only permitted
check.

## Why `.git` is included here but not in `/retire`

Retire drops `.git` because the archive is a working copy and history stays
with the git remote — which is why it *blocks* on a missing remote. A backup
exists to survive loss, so it must carry its own history. A project with no
remote (aidc, today) would otherwise be backed up with its entire history
silently missing.

Consequence worth knowing: `.git` is thousands of small files, so the first
backup of a large repo is slow and noisy for Drive's sync client. That is the
correct trade for a backup.

## Sequence

**1. Dry run — always first.**

```powershell
C:\Users\kashi\workspace\_project_kit\backup-project.ps1 -Project <name>
```

Report the file count, size, and every WARN. Warnings here are *information*,
not blockers — an uncommitted tree is exactly what a backup is protecting.
Do not offer to commit or push first unless Kashi asks; that would defeat the
point of backing the current state up.

**2. Copy.**

```powershell
...\backup-project.ps1 -Project <name> -Apply
```

Read back the `carried over:` lines for `.secrets`, `.raw`, `.output`, `data`,
`src`, `config`, `static`, `.git`. Any `MISSING in copy:` line is a real
problem — report it, do not paper over it.

**3. Report.** Where it went, size, what was excluded, and anything the
warnings revealed that Kashi may want to act on (no remote, unpushed commits).

## `-Mirror` — only when asked

By default the backup overwrites in place and leaves destination files that no
longer exist in the source, so the archive slowly accumulates deleted files.
`-Mirror` makes it an exact reflection — and **deletes at the destination**.
Never pass it on your own initiative; it can remove the only copy of something
that was deleted from the workspace deliberately.

## What travels

Everything the project needs to run and its history: source, data, config,
docs, `.git`, and deliberately `.secrets`, `.raw`, `.output` / `output`.

Excluded (recreatable or machine-local): `.claude`, `.venv`, `venv`,
`__pycache__`, `.pytest_cache`, `.ruff_cache`, `.mypy_cache`, `node_modules`,
`build`, `dist`, `.ipynb_checkpoints`, `.zed`, `*.stackdump`, `*.pyc`.

The exclusion list lives in `_project_kit/lib/project-copy.ps1` and is shared
with `/retire`. Change it there, never in one script only.

## Standing rules

- Dry run first, every time.
- Never read `.secrets`.
- Never pass `-Mirror` unless Kashi asks for it.
- Never delete, move, or de-register anything — that is `/retire`'s job. If the
  intent is actually to retire a finished project, say so and use `/retire`.
- A project being actively edited in another session is fine to back up; say
  which files were dirty at the time so the snapshot is understood.
