# sync-skills.ps1 — push canonical kit skills into project repos.
# The kit (templates/.claude/skills) is the single source of truth.
# Improve a skill IN THE KIT, then run this to fan it out.
#
# Usage:
#   .\sync-skills.ps1            # report drift only (dry run)
#   .\sync-skills.ps1 -Apply     # overwrite project copies with kit versions
#
# If a project copy is AHEAD of the kit (you improved it in-project), the
# report shows DRIFT — diff it, backport to the kit first, then -Apply.

param([switch]$Apply)

$Kit = Join-Path $PSScriptRoot 'templates\.claude\skills'
$Projects = @(
    'C:\Users\kashi\workspace\python\mktdb',
    'C:\Users\kashi\workspace\python\zp_scm'
)

$drift = 0
foreach ($skillDir in Get-ChildItem $Kit -Directory) {
    $src = Join-Path $skillDir.FullName 'SKILL.md'
    foreach ($proj in $Projects) {
        $dst = Join-Path $proj ".claude\skills\$($skillDir.Name)\SKILL.md"
        $projName = Split-Path $proj -Leaf
        if (-not (Test-Path $dst)) {
            $state = 'MISSING'
        } elseif ((Get-FileHash $src).Hash -eq (Get-FileHash $dst).Hash) {
            $state = 'in sync'
        } else {
            $state = 'DRIFT'
        }
        if ($state -ne 'in sync') {
            $drift++
            if ($Apply) {
                New-Item -ItemType Directory -Force (Split-Path $dst) | Out-Null
                Copy-Item $src $dst -Force
                "{0,-20} {1,-8} {2} -> synced" -f $skillDir.Name, $projName, $state
            } else {
                "{0,-20} {1,-8} {2}" -f $skillDir.Name, $projName, $state
            }
        }
    }
}
if ($drift -eq 0) { 'All project skills in sync with kit.' }
elseif (-not $Apply) { "`n$drift out of sync. Diff any DRIFT before running with -Apply (a project copy may be ahead of the kit)." }
