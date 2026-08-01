# project-kit — reusable Claude Code project starter

A portable bootstrap for spec-driven, feature-by-feature Claude Code projects
with token-economy discipline, enforced state-sync via hooks, and a clean
git/Drive separation.

## What's in here
```
project-kit/
├── PATTERNS.md            # THE CANON — decided conventions + why they exist
├── STARTUP_PROMPT.md      # Paste into Claude Code in a fresh folder (the centerpiece)
├── new-project.ps1         # Windows bootstrap (run once in an empty folder)
├── new-project.sh          # bash/WSL/mac/Linux bootstrap
├── sync-skills.ps1         # push canonical kit skills out to live projects
├── backup-project.ps1      # copy a LIVE project to Drive (see /backup skill)
├── retire-project.ps1      # archive a FINISHED project + remove it (/retire)
├── lib/project-copy.ps1    # shared copy engine + exclusion list for both
├── lessons/                # notes rescued from retired projects
└── templates/              # Files copied into each new project
    ├── CLAUDE.md            # Persistent instructions (with {{PLACEHOLDERS}})
    ├── PLAN.md / PROGRESS.md / ARCHITECTURE.md / DOMAIN.md / README.md / spec.md
    ├── .gitignore / .driveignore
    └── .claude/
        ├── settings.json        # Hooks wiring + permissions (toolchain placeholders)
        ├── hooks/                # PreCompact (blocks), PostToolUse, Stop, SessionStart
        └── skills/               # feature-build-loop, brand-visuals, find-icon
```

## One-time setup (do this once)
1. Put this `project-kit` folder somewhere stable, e.g. `C:\Users\you\project-kit`.
2. Optionally make a shell alias / PATH shortcut so you can call the bootstrap
   from anywhere.

## Per new project
1. Create + enter a new empty folder.
2. Run the bootstrap from there:
   - PowerShell: `powershell -ExecutionPolicy Bypass -File C:\Users\kashi\workspace\_project_kit\new-project.ps1`
   - bash:       `bash C:/Users/kashi/workspace/_project_kit/new-project.sh`
   It refuses to run in a non-empty folder (asks first), copies templates,
   makes folder stubs, and prints next steps. **It does NOT run git or installs
   or invoke Claude** — that's the permission gate.
3. Open `STARTUP_PROMPT.md`, fill in the `{{PLACEHOLDERS}}` (toolchain, OS,
   brand palette).
4. Also fill placeholders in `templates`-copied files now sitting in your
   folder: `.claude/settings.json` (the `__YOUR_*__` tool perms),
   `.claude/hooks/post_edit_stage.sh` (LINTER_FIX / LINTER_FORMAT),
   CLAUDE.md, README.md, and skills' `{{HEX}}` palette.
5. Launch `claude`, paste STARTUP_PROMPT.md as your first message. Claude
   proposes a plan and asks permission before creating/initializing anything.

## Keeping skills in sync
`templates/.claude/skills/` is the single source of truth for kit skills. Improve
a skill in the kit, then fan it out to the live projects it targets:
```
.\sync-skills.ps1            # report drift only (dry run)
.\sync-skills.ps1 -Apply     # overwrite project copies with kit versions
```
Target projects are hardcoded in the script's `$Projects` list — update that list
when adding/removing a project. If a project copy is AHEAD of the kit (improved
in-project), the report shows DRIFT — diff and backport to the kit before `-Apply`.

## Windows hooks note
The hooks are bash `.sh` scripts. They fire if Git Bash (or WSL) is on PATH —
check with `bash --version`. If bash isn't available, convert the four hook
scripts to PowerShell (`.ps1`) and update the `command` paths in settings.json
accordingly. The PreCompact BLOCK behavior depends on the hook returning a
non-zero exit code, which both bash and PowerShell support.

## PATTERNS.md — how to add to the canon
`PATTERNS.md` holds the decided conventions (LLM provider layer, config
layers, plug-and-play manifests, redact-at-data-layer, standalone export,
feature-index generation, brand law), each recorded with the failure that
motivated it. `/advisor` audits projects against it.

To add one: say **"enshrine X"** in any session. It gets generalized, written
up with its motivating failure, and fanned out. A pattern with no recorded
failure is a style opinion — it stays out.

## Backing up a live project
`/backup <project>` (skill) drives `backup-project.ps1`: copies the project to
`G:\My Drive\_projects\<name>` and changes nothing else — the workspace copy,
the registries and git are all untouched. Re-run it as often as you like.

Unlike `/retire` it **includes `.git`** and **never blocks**: uncommitted work,
unpushed commits and a missing remote are the conditions a backup exists for,
so they are reported, not refused. `-Mirror` makes it an exact reflection but
deletes at the destination — opt in only.

## Retiring a finished project
`/retire <project>` (skill) drives `retire-project.ps1`: archives the project
to **`G:\My Drive\_projects\zArchive\<name>`** as a **runnable working copy** —
source, data, config, plus `.secrets`, `raw`, `output` — excluding everything
recreatable (`.claude`, `.venv`, caches, build output).

Retired projects go to `zArchive/`, not `_projects/`, because `/backup` writes
*live* projects into `_projects/` — a retired folder beside them would read as
live and the two could overwrite each other.

`.git` travels only when it has to: if a remote already holds the history it is
excluded and the archive is a clean working copy; if there is no remote, or
commits that never reached one, `.git` is carried in and the archive becomes the
copy of record. **A missing remote is a warning, not a blocker** — small
projects (a deck builder, a one-off generator) never need a GitHub repo.

Always dry-runs first. It blocks only on uncommitted changes and on an archive
of that name already existing. Copy and source-removal are separate steps;
removal asks you to type the project name.

After removal the skill updates every registry that named the project
(CLAUDE.md, PORTS.md, `$Projects` in sync-skills.ps1) — skipping that is how
phantom projects survive for months.

## The core conventions this kit enforces
- spec.md is append-only `## Feature N` sections; no manual "Core" section —
  Claude decides core-vs-feature and reports it.
- PLAN.md = current state (overwritten); PROGRESS.md = append-only log/index.
- PreCompact hook blocks compaction if code changed but state files didn't.
- Model routing: mid-tier default, top model + Plan Mode for architectural
  features, frontier model only when stuck, lightest model for trivial work.
- Git is source of truth; Drive is a separate human-share channel (never
  mirror Drive Desktop onto the live working tree).
- .secrets/.env: git-ignored always, Drive-shareable if you designate Drive secure.
