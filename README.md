# project-kit — reusable Claude Code project starter

A portable bootstrap for spec-driven, feature-by-feature Claude Code projects
with token-economy discipline, enforced state-sync via hooks, and a clean
git/Drive separation.

## What's in here
```
project-kit/
├── STARTUP_PROMPT.md      # Paste into Claude Code in a fresh folder (the centerpiece)
├── new-project.ps1         # Windows bootstrap (run once in an empty folder)
├── new-project.sh          # bash/WSL/mac/Linux bootstrap
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

## Windows hooks note
The hooks are bash `.sh` scripts. They fire if Git Bash (or WSL) is on PATH —
check with `bash --version`. If bash isn't available, convert the four hook
scripts to PowerShell (`.ps1`) and update the `command` paths in settings.json
accordingly. The PreCompact BLOCK behavior depends on the hook returning a
non-zero exit code, which both bash and PowerShell support.

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
