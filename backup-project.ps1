# backup-project.ps1 — copy a LIVE project to Drive. Nothing is deleted, nothing
# is de-registered, the workspace copy is untouched.
#
#   .\backup-project.ps1 -Project mktdb                 # dry run (default)
#   .\backup-project.ps1 -Project mktdb -Apply          # copy / refresh
#   .\backup-project.ps1 -Project mktdb -Apply -Mirror  # exact reflection
#   .\backup-project.ps1 -All -Apply                    # every live project
#
# Sibling of retire-project.ps1, and they share lib/project-copy.ps1 so the two
# can never disagree about what a project is made of.
#
# THREE DELIBERATE DIFFERENCES FROM /retire
#
# 1. .git IS copied. Retire drops it because history stays with the git remote
#    and the archive is only a working copy. A backup exists to survive loss, so
#    it must carry its own history — a project with no remote (aidc today) would
#    otherwise be backed up with its entire history silently missing.
#
# 2. Nothing blocks. Uncommitted changes, unpushed commits and a missing remote
#    are the exact conditions a backup is FOR. They are reported, never refused.
#
# 3. Re-runnable. Overwrites the previous backup in place without asking, since
#    that is the normal case. Use -Mirror for an exact reflection — it DELETES
#    files at the destination that no longer exist in the source.

[CmdletBinding()]
param(
    [string]$Project,
    [switch]$All,
    [switch]$Apply,
    [switch]$Mirror,
    [string[]]$Skip = @(),
    [string]$SourceRoot = 'C:\Users\kashi\workspace\python',
    [string]$DestRoot   = 'G:\My Drive\_projects'
)

$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\lib\project-copy.ps1"

if (-not $Project -and -not $All) {
    Write-Host "Specify -Project <name> or -All." -ForegroundColor Yellow
    Get-ChildItem $SourceRoot -Directory | ForEach-Object { "  $($_.Name)" }
    exit 1
}
if (-not (Test-Path $DestRoot)) {
    Write-CopyFail "backup root not reachable: $DestRoot (is Drive mounted?)"
    exit 1
}

$targets = if ($All) {
    Get-ChildItem $SourceRoot -Directory |
        Where-Object { $_.Name -notin $Skip } |
        Select-Object -ExpandProperty Name
} else { @($Project) }

$failed = 0
foreach ($name in $targets) {
    $src = Join-Path $SourceRoot $name
    $dst = Join-Path $DestRoot   $name

    Write-Host "`n=== backup: $name ===" -ForegroundColor Cyan
    Write-Host "  source: $src"
    Write-Host "  backup: $dst"

    if (-not (Test-Path $src)) { Write-CopyFail "no such project: $src"; $failed++; continue }

    # Reported, never blocking — an uncommitted tree is precisely what a backup
    # is protecting. Retire refuses these; backup only tells you.
    if (Test-Path (Join-Path $src '.git')) {
        Push-Location $src
        try {
            $dirty = git status --porcelain 2>$null
            if ($dirty) { Write-CopyWarn "$(($dirty | Measure-Object -Line).Lines) uncommitted file(s) — included as-is." }
            else { Write-CopyOk 'working tree clean' }
            if (-not (git remote 2>$null)) {
                Write-CopyWarn 'no git remote — this backup is the ONLY copy of its history.'
            } else {
                $unpushed = git log --branches --not --remotes --oneline 2>$null
                if ($unpushed) { Write-CopyWarn "$(($unpushed | Measure-Object -Line).Lines) unpushed commit(s) — included via .git." }
            }
        } finally { Pop-Location }
    } else {
        Write-CopyWarn 'not a git repo — no history to carry.'
    }

    if ($Mirror -and $Apply -and (Test-Path $dst)) {
        Write-CopyWarn '-Mirror DELETES destination files missing from the source.'
    }

    $rc = Invoke-ProjectCopy -Source $src -Dest $dst -IncludeGit -Mirror:$Mirror -ListOnly:(-not $Apply)
    if ($rc -ge 8) { Write-CopyFail "robocopy failed with exit code $rc"; $failed++; continue }
    if (-not $Apply) { continue }

    $missing = Test-ProjectCarriedOver -Source $src -Dest $dst -IncludeGit
    if ($missing -gt 0) { $failed++ }

    $files = (Get-ChildItem $dst -Recurse -File -Force -ErrorAction SilentlyContinue | Measure-Object)
    $size  = (Get-ChildItem $dst -Recurse -File -Force -ErrorAction SilentlyContinue |
        Measure-Object -Property Length -Sum).Sum / 1MB
    Write-CopyOk ("{0} files, {1:N1} MB -> {2}" -f $files.Count, $size, $dst)
}

Write-Host ''
if (-not $Apply) {
    Write-Host 'Dry run only. Nothing was copied. Re-run with -Apply.' -ForegroundColor Cyan
} elseif ($failed) {
    Write-Host "$failed project(s) reported problems — see WARN/BLOCKED above." -ForegroundColor Yellow
    exit 1
} else {
    Write-Host 'Backup complete. The workspace copy is untouched.' -ForegroundColor Green
}
# Explicit: robocopy exits 1 for "files copied", which would otherwise leak out
# as this script's exit code and read as a failure.
exit 0
