# retire-project.ps1 — archive a completed project to Drive, then optionally
# remove it from the workspace.
#
#   .\retire-project.ps1 -Project aidc                    # dry run (default)
#   .\retire-project.ps1 -Project aidc -Apply             # copy to Drive
#   .\retire-project.ps1 -Project aidc -Apply -Force      # overwrite existing archive
#   .\retire-project.ps1 -Project aidc -RemoveSource      # delete workspace copy
#                                                         # (only after a verified copy)
#
# What is copied: everything the project needs to run again from the archive —
# source, data, config, docs, and deliberately `.secrets`, `raw`, `output`.
# Secrets are copied by robocopy at the file level; nothing reads their contents.
#
# What is NOT copied: recreatable or machine-local state — .git, .claude,
# .venv, __pycache__, .pytest_cache, .ruff_cache, .mypy_cache, node_modules,
# build, dist, egg-info, notebook checkpoints, crash dumps.
#
# NOTE ON .git: the archive is a working copy, not a repo. History stays with
# the git remote. If a project has NO remote, the script blocks — archiving it
# would discard the entire history.

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Project,
    [switch]$Apply,
    [switch]$Force,
    [switch]$RemoveSource,
    [string]$SourceRoot = 'C:\Users\kashi\workspace\python',
    [string]$DestRoot   = 'G:\My Drive\_projects'
)

$ErrorActionPreference = 'Stop'
# Shared with backup-project.ps1 — one definition of what a project is made of.
. "$PSScriptRoot\lib\project-copy.ps1"

$src = Join-Path $SourceRoot $Project
$dst = Join-Path $DestRoot   $Project

function Fail($msg) { Write-CopyFail $msg; exit 1 }
function Warn($msg) { Write-CopyWarn $msg }
function Ok($msg)   { Write-CopyOk $msg }

Write-Host "`n=== retire: $Project ===" -ForegroundColor Cyan
Write-Host "  source: $src"
Write-Host "  archive: $dst`n"

# --- Pre-flight -----------------------------------------------------------
if (-not (Test-Path $src)) { Fail "no such project: $src" }
if (-not (Test-Path $DestRoot)) { Fail "archive root not reachable: $DestRoot (is Drive mounted?)" }

Push-Location $src
try {
    if (Test-Path (Join-Path $src '.git')) {
        $dirty = git status --porcelain 2>$null
        if ($dirty) {
            if (-not $Force) { Fail "uncommitted changes ($(($dirty | Measure-Object -Line).Lines) files). Commit first, or pass -Force." }
            Warn "uncommitted changes are being archived as-is (-Force)."
        } else { Ok 'working tree clean' }

        $remote = git remote 2>$null
        if (-not $remote) {
            if (-not $Force) { Fail "no git remote — archiving drops all history. Add a remote and push, or pass -Force to archive anyway." }
            Warn 'no git remote: history will be lost when the workspace copy is removed.'
        } else {
            $unpushed = git log --branches --not --remotes --oneline 2>$null
            if ($unpushed) {
                if (-not $Force) { Fail "$(($unpushed | Measure-Object -Line).Lines) unpushed commit(s). Push first, or pass -Force." }
                Warn 'unpushed commits: history beyond the remote will be lost.'
            } else { Ok 'all commits pushed to remote' }
        }
    } else {
        Warn 'not a git repo — nothing to verify against a remote.'
    }
} finally { Pop-Location }

# Is the app still running on its registered port?
$ports = Select-String -Path (Join-Path (Split-Path $SourceRoot -Parent) 'PORTS.md') `
    -Pattern "python/$Project\D+\*\*(\d{2,5})\*\*" -ErrorAction SilentlyContinue
foreach ($m in $ports) {
    $port = $m.Matches[0].Groups[1].Value
    $live = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($live) { Warn "port $port is LISTENING — '$Project' may still be running. Stop it before removing the source." }
}

if (Test-Path $dst) {
    $existing = (Get-ChildItem $dst -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count
    if (-not $Force) { Fail "archive already exists with $existing file(s): $dst`n         Re-run with -Force to overwrite it." }
    Warn "overwriting existing archive ($existing files) at $dst"
}

# --- Copy -----------------------------------------------------------------
# No -IncludeGit: the archive is a working copy, history stays with the remote.
# That is exactly why the pre-flight above refuses a project with no remote.
$rc = Invoke-ProjectCopy -Source $src -Dest $dst -ListOnly:(-not $Apply)
if ($rc -ge 8) { Fail "robocopy failed with exit code $rc" }

if (-not $Apply) {
    Write-Host "`nDry run only. Nothing was copied. Re-run with -Apply." -ForegroundColor Cyan
    exit 0   # not $LASTEXITCODE — robocopy's 1 means "would copy", not failure
}

# --- Verify ---------------------------------------------------------------
$dstCount = (Get-ChildItem $dst -Recurse -File -Force -ErrorAction SilentlyContinue | Measure-Object).Count
$dstSize  = (Get-ChildItem $dst -Recurse -File -Force -ErrorAction SilentlyContinue |
    Measure-Object -Property Length -Sum).Sum / 1MB

Write-Host ''
Ok ("archived {0} files, {1:N1} MB -> {2}" -f $dstCount, $dstSize, $dst)

$missing = Test-ProjectCarriedOver -Source $src -Dest $dst
if ($missing -gt 0) { Fail "$missing expected folder(s) missing from the archive — do NOT remove the source." }

# --- Remove source (explicit, last) --------------------------------------
if ($RemoveSource) {
    if ($dstCount -eq 0) { Fail 'refusing to remove source: archive is empty.' }
    Write-Host ''
    Write-Host "About to DELETE $src" -ForegroundColor Red
    $ans = Read-Host "Type the project name ('$Project') to confirm"
    if ($ans -ne $Project) { Write-Host 'Aborted. Source left in place.'; exit 1 }
    Remove-Item $src -Recurse -Force
    Ok "removed workspace copy: $src"
    Write-Host ''
    Write-Host 'Now update the registries (the /retire skill does this):' -ForegroundColor Cyan
    Write-Host '  - workspace CLAUDE.md : move the row to "Retired"'
    Write-Host '  - PORTS.md            : free the port slot'
    Write-Host '  - sync-skills.ps1     : drop it from $Projects'
} else {
    Write-Host ''
    Write-Host "Source left in place. When you are satisfied with the archive:" -ForegroundColor Cyan
    Write-Host "  .\retire-project.ps1 -Project $Project -RemoveSource"
}

# Explicit: robocopy exits 1 for "files copied", which would otherwise leak out
# as this script's exit code and read as a failure.
exit 0
