# project-copy.ps1 — shared copy logic for retire-project.ps1 and
# backup-project.ps1. Dot-source it; do not run it directly.
#
#   . "$PSScriptRoot\lib\project-copy.ps1"
#
# One definition of "what a project is made of", so /retire and /backup can
# never drift into disagreeing about it.

# Recreatable or machine-local state. Never worth copying anywhere.
$ProjectExcludeDirs = @(
    '.claude', '.venv', 'venv', '__pycache__', '.pytest_cache',
    '.ruff_cache', '.mypy_cache', 'node_modules', 'build', 'dist',
    '.ipynb_checkpoints', '.zed'
)
$ProjectExcludeFiles = @('*.stackdump', '*.pyc')

# .git is excluded by /retire (history stays with the remote, and the archive is
# a working copy) but INCLUDED by /backup (a backup whose whole purpose is
# surviving loss must carry its own history). Callers decide.
$ProjectGitDir = '.git'

function Write-CopyFail { param($m) Write-Host "BLOCKED: $m" -ForegroundColor Red }
function Write-CopyWarn { param($m) Write-Host "WARN:    $m" -ForegroundColor Yellow }
function Write-CopyOk   { param($m) Write-Host "ok:      $m" -ForegroundColor Green }

function Invoke-ProjectCopy {
    <#
      Copies $Source to $Dest with the shared exclusions.
      -IncludeGit  keep .git (backup) instead of dropping it (retire)
      -Mirror      delete files at the destination that no longer exist in the
                   source. Exact reflection, but destructive at the far end.
      -ListOnly    robocopy /L — report what would happen, copy nothing.
      Returns the robocopy exit code (< 8 is success).
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$Dest,
        [switch]$IncludeGit,
        [switch]$Mirror,
        [switch]$ListOnly
    )

    $xd = @($ProjectExcludeDirs)
    if (-not $IncludeGit) { $xd += $ProjectGitDir }

    $rcArgs = @($Source, $Dest, '/R:1', '/W:1', '/NFL', '/NDL', '/NJH', '/NP')
    $rcArgs += $(if ($Mirror) { '/MIR' } else { '/E' })
    $rcArgs += '/XD'; $rcArgs += $xd
    $rcArgs += '/XF'; $rcArgs += $ProjectExcludeFiles
    if ($ListOnly) { $rcArgs += '/L' }

    Write-Host ("`n{0}robocopy {1}`n" -f $(if ($ListOnly) { 'DRY RUN: ' } else { '' }), ($rcArgs -join ' ')) -ForegroundColor DarkGray
    & robocopy @rcArgs | Out-Host
    return $LASTEXITCODE
}

function Test-ProjectCarriedOver {
    <#
      Confirms the folders that matter actually landed. .secrets is checked by
      PRESENCE ONLY — never read its contents, not even to verify a copy.
    #>
    param(
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$Dest,
        [switch]$IncludeGit
    )
    $must = @('.secrets', '.raw', '.output', 'output', 'data', 'src', 'config', 'static')
    if ($IncludeGit) { $must += '.git' }
    $missing = 0
    foreach ($m in $must) {
        if (Test-Path (Join-Path $Source $m)) {
            if (Test-Path (Join-Path $Dest $m)) { Write-CopyOk "carried over: $m" }
            else { Write-CopyWarn "MISSING in copy: $m"; $missing++ }
        }
    }
    return $missing
}
