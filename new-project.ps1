# new-project.ps1
# One-shot bootstrap for a new spec-driven Claude Code project.
# Usage (from inside a NEW empty folder):
#   powershell -ExecutionPolicy Bypass -File C:\path\to\new-project.ps1
#
# What it does:
#   1. Refuses to run if the folder isn't empty (safety).
#   2. Copies the template files (.claude hooks/skills, .gitignore,
#      .driveignore, state-file stubs, manifest) into the current folder.
#   3. Prints the startup prompt path so you can paste it into Claude Code,
#      which will then ask YOUR permission before doing anything further.
#
# This is the "ask my permission" gate: the script only stages templates;
# Claude does nothing until you paste STARTUP_PROMPT.md and approve.

$ErrorActionPreference = "Stop"
$KitRoot = "$PSScriptRoot"   # the kit lives wherever this script lives
$Target  = (Get-Location).Path

# --- 1. Safety: only run in an (almost) empty folder ---
$existing = Get-ChildItem -Force | Where-Object { $_.Name -notin @('.','..') }
if ($existing.Count -gt 0) {
    Write-Host "Folder is not empty. Found:" -ForegroundColor Yellow
    $existing | ForEach-Object { Write-Host "  $($_.Name)" }
    $ans = Read-Host "Proceed anyway and copy templates in? (y/N)"
    if ($ans -ne 'y') { Write-Host "Aborted."; exit 1 }
}

# --- 2. Copy templates ---
Write-Host "Copying project templates into $Target ..." -ForegroundColor Cyan
Copy-Item -Recurse -Force "$KitRoot\templates\*" $Target

# Make folder stubs
$dirs = @("src", "tests", "data")
foreach ($d in $dirs) {
    if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d | Out-Null }
    if (-not (Test-Path "$d\.gitkeep")) { New-Item -ItemType File -Path "$d\.gitkeep" | Out-Null }
}

# --- 3. Hand off to Claude Code (permission-gated) ---
Write-Host ""
Write-Host "Templates staged. Nothing else has run." -ForegroundColor Green
Write-Host ""
Write-Host "NEXT STEPS:" -ForegroundColor Cyan
Write-Host "  1. Fill in the {{PLACEHOLDERS}} in STARTUP_PROMPT.md (toolchain, OS, brand)."
Write-Host "  2. Launch Claude Code:   claude"
Write-Host "  3. Paste the contents of STARTUP_PROMPT.md as your first message."
Write-Host "     Claude will propose a plan and ASK before creating/initializing anything."
Write-Host ""
Write-Host "  (STARTUP_PROMPT.md is in this folder now.)"
