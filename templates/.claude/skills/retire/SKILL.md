---
name: retire
description: Retire a completed project — archive it to G:\My Drive\_projects\zArchive as a runnable working copy, verify, remove it from the workspace, and update every registry that referenced it. Destructive; always dry-runs first.
---

# /retire — archive a completed project

Counterpart to `/advisor`. Where `/advisor` decides *whether* something is done,
this moves it out cleanly.

`/retire <project>` — e.g. `/retire aidc`. No argument: list the workspace
projects with last-commit dates and ask which one.

The script does the copying: `_project_kit/retire-project.ps1`. **Never
hand-roll the copy** — the script encodes the exclusion list, the safety
pre-flight, and the verification. Your job is to run it, read the output, and
update the registries afterwards.

## Never read `.secrets`

`.secrets/` is copied to the archive because the project must run again from
there. It is copied **by robocopy, at the file level**. Do not `Read`, `cat`,
`Get-Content`, grep or otherwise open any file under `.secrets/` at any point
in this workflow — not to verify, not to summarise, not to check it copied.
The script's presence check (`Test-Path`) is the only verification needed and
the only one permitted.

## Sequence

**1. Dry run — always first, no exceptions.**

```powershell
C:\Users\kashi\workspace\_project_kit\retire-project.ps1 -Project <name>
```

Report to Kashi: what would copy (file count, size), and every BLOCKED or WARN
line. Common blocks and what they mean:

| Signal | Blocks? | Meaning |
|---|---|---|
| uncommitted changes | **yes** | work would be archived un-versioned; committing first is trivial and lossless |
| archive already exists | **yes** | a folder of that name is already in `zArchive` — **ask Kashi** before `-Force` |
| no git remote | no | `.git` is carried into the archive instead; it becomes the only copy of that history |
| unpushed commits | no | same — `.git` travels so the commits are not lost |
| port LISTENING | no | the app may still be running; stop it before removing the source |

**Do not pass `-Force` to clear a block without asking.** Both blocks protect
something irreversible. The "archive already exists" case is the one Kashi
explicitly wants to be asked about — say how many files the existing archive
holds and when it was last written, then let him decide.

A missing remote is deliberately **not** a blocker: plenty of small projects (a
deck builder, a one-off generator) never justify a GitHub repo. Do not push
Kashi to create one. Just report that the archive now carries the history.

**2. Copy, on approval.**

```powershell
...\retire-project.ps1 -Project <name> -Apply           # add -Force only if approved
```

Read the verification block back: archived file count and size, plus the
`carried over:` lines for `.secrets`, `raw`, `output`, `data`, `src` (and
`.git` when it travelled). Any `MISSING in copy:` line stops the workflow —
report it and do not proceed to removal.

**3. Remove the workspace copy — only after Kashi confirms the archive is good.**

```powershell
...\retire-project.ps1 -Project <name> -RemoveSource
```

This prompts for the project name interactively as a typed confirmation. It is
the only destructive step and it is deliberately separate from the copy.

**4. Update every registry that named the project.** This is the part that
rots if skipped — a stale registry briefs every future session with false
context, which is exactly how three phantom projects survived for months.

- `workspace/CLAUDE.md` — move the row out of the Active Projects table into
  the `Retired:` note, with the reason and the date.
- `workspace/PORTS.md` — remove the row, and add the freed port back to the
  "Free for new dashboards" line.
- `_project_kit/sync-skills.ps1` — drop it from `$Projects`.
- Any project memory in `~/.claude/projects/.../memory/` that describes it as
  active — update or delete it.

Commit those in the workspace and kit repos with a message naming what was
retired and where it went.

**5. Report.** Where the archive is, its size, what was excluded, whether
`.git` travelled, what registries changed, and how to bring it back: copy the
folder back into `workspace/python/`, `git clone` the remote over it if the
history stayed with the remote, then `uv sync`.

## Where it goes

`G:\My Drive\_projects\zArchive\<name>` — **not** `_projects\<name>`.

`/backup` writes *live* projects into `_projects\`, so a retired folder sitting
beside them would read as live, and the two could overwrite each other. The
script warns if a stale `/backup` copy of the same project is still in
`_projects\` after retiring; report it and let Kashi delete it — never delete
it unasked.

## What travels and what does not

Copied: source, data, config, docs, and deliberately `.secrets`, `raw`,
`output` — the archive must be *runnable*, not just readable.

Excluded (recreatable or machine-local): `.claude`, `.venv`, `venv`,
`__pycache__`, `.pytest_cache`, `.ruff_cache`, `.mypy_cache`, `node_modules`,
`build`, `dist`, `.ipynb_checkpoints`, `.zed`, `*.stackdump`, `*.pyc`.

**`.git` depends on where the history lives.** The script decides and reports:

- remote holds everything → `.git` excluded, the archive is a clean working
  copy and history stays with the remote;
- no remote, or commits that never reached one → `.git` is carried **into** the
  archive, which then holds the only copy of that history.

History always survives somewhere. That is why a missing remote is a warning
rather than a refusal.

## Standing rules

- Dry run first, every time.
- Never `-Force` past a block without explicit approval.
- Never remove the source in the same step as the copy.
- Never read `.secrets`.
- If the project is one Kashi is actively working in another session, stop and
  say so rather than archiving underneath it.
