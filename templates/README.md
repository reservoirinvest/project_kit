# {{PROJECT_NAME}}

{{ONE_LINE_DESCRIPTION}}

Built feature-by-feature against `spec.md`.

## Setup
```
{{INSTALL_COMMAND}}
```
For collaborators without {{PKG_MANAGER}}:
```
{{FALLBACK_INSTALL_COMMAND}}
```

## Structure
```
{{PROJECT_NAME}}/
├── spec.md           # Feature specs — source of truth
├── PLAN.md            # Current feature status
├── PROGRESS.md        # Append-only build log
├── ARCHITECTURE.md    # Design decisions + principles
├── DOMAIN.md          # Project glossary / memory
├── CLAUDE.md           # Instructions for Claude Code
├── src/
│   ├── core/                # Shared logic
│   ├── utils/                # Pure helpers
│   └── features/             # One subfolder per spec feature
├── tests/
└── data/
```

## Data & secrets
- `.env` holds secrets — never committed to git. Shareable via Drive if that's
  your secure channel (see `.driveignore`; do not point Drive Desktop at this
  folder directly).

## Status
See PROGRESS.md (build log) and PLAN.md (in-flight work).
