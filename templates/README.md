# {{PROJECT_NAME}}

{{ONE_LINE_DESCRIPTION}}

Built feature-by-feature against `spec.md`.

## Setup
```
{{INSTALL_COMMAND}}
```
This installs the project itself (editable), which is what puts the
`{{PROJECT_NAME}}` command on the path. For collaborators without
{{PKG_MANAGER}}:
```
{{FALLBACK_INSTALL_COMMAND}}
```

## Run
```
uv run {{PROJECT_NAME}}            # canonical entry point
uv run {{PROJECT_NAME}} --help     # what it accepts
```
The command comes from `[project.scripts]` in `pyproject.toml`. Never document
`uv run python -m src.<module>`, `uvicorn ...` or a raw `python` invocation as
the primary way to run this — those are implementation detail, and they break
the moment a module moves.

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
- `.secrets/.env` holds secrets — never committed to git. Shareable via Drive if
  that's your secure channel (see `.driveignore`; do not point Drive Desktop at
  this folder directly).

## OAuth Setup (Ask AI via Claude Code subscription)

If this project has an LLM-backed feature (Ask AI, chat, etc.), it can query
Claude two ways:
- **`ANTHROPIC_API_KEY`** — pay-per-token, metered Anthropic API billing.
- **`CLAUDE_CODE_OAUTH_TOKEN`** — routes the same query through the Claude
  Agent SDK (`claude-agent-sdk`), which runs the `claude` CLI headlessly and
  bills against your **Claude Code Max/Pro subscription** instead of the API.
  No API key needed for that path.

**Generate the token** (requires the `claude` CLI installed and logged in
locally):
```
claude setup-token
```
This prints a long-lived OAuth token (`sk-ant-oat01-...`).

**Where to store it:** add it to `.secrets/.env` (never commit it — same rules as
any other secret in this project):
```
CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-...
```

**Usage quota warning (Max plan):** the OAuth path spends your Claude Code
subscription's **session-based usage limits** (5-hour rolling windows), not
API dollars — it competes with any Claude Code CLI sessions you run
concurrently on the same account. On the Max plan this is generous but not
unlimited; if the dashboard's Ask AI feature is hit heavily (many users,
tight polling, agentic loops), prefer the `ANTHROPIC_API_KEY` path instead, or
you may see Claude Code itself throttled. There is no separate token/cost
counter for this path — check usage via `claude` CLI status, not the
Anthropic Console (that only shows API-key spend).

## Status
See PROGRESS.md (build log) and PLAN.md (in-flight work).
