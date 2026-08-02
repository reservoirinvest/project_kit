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

param(
    [switch]$Apply,
    # Skip projects by folder name when a session is actively editing them:
    #   .\sync-skills.ps1 -Apply -Skip kite
    [string[]]$Skip = @()
)

$Kit = Join-Path $PSScriptRoot 'templates\.claude\skills'

# advisor / backup / retire are workspace-scoped — they operate on
# C:\Users\kashi\workspace paths and already exist as user-level skills
# (~/.claude/skills). Syncing them into a project would duplicate them
# uselessly AND bake Kashi's name/absolute paths into that project's git
# history — a real leak for client-skinned repos. Kit template copies stay as
# documentation of record; they just don't fan out.
$WorkspaceScoped = @('advisor', 'backup', 'retire')

# Every project carrying kit skills must be listed here, or its copies drift
# invisibly — kite held 5 skills unmanaged for weeks because it was missing.
#
# `Brand` is where that project serves brand.css from; projects disagree because
# their static roots do. $null means "do not fan brand.css here":
#   zp_scm — carries a deliberate Zuellig client livery, not the registry
#   aidc   — its brand.css is still the TCS-derived theme, and its deck uses 15
#            token names the RKV seed does not define (--surface-elevated,
#            --cta-bg, --shadow-*, --radius-*, --brand-yellow, --status-orange).
#            Overwriting would not re-skin it, it would break it. Migrating aidc
#            onto the registry is its own feature.
#   ibd    — frozen at tag ibd-frozen, read-only; not listed at all
$Projects = @(
    @{ Path = 'C:\Users\kashi\workspace\python\ibf';    Brand = 'static\brand.css' }
    @{ Path = 'C:\Users\kashi\workspace\python\kite';   Brand = 'static\brand.css' }
    @{ Path = 'C:\Users\kashi\workspace\python\mktdb';  Brand = 'static\css\brand.css' }
    @{ Path = 'C:\Users\kashi\workspace\python\zp_scm'; Brand = $null }
    @{ Path = 'C:\Users\kashi\workspace\python\aidc';   Brand = $null }
) | Where-Object { (Split-Path $_.Path -Leaf) -notin $Skip -and (Test-Path $_.Path) }

if ($Skip.Count) { "Skipping: $($Skip -join ', ')`n" }

$script:drift = 0

# Reports and counts, but deliberately RETURNS nothing: in PowerShell an
# uncaptured string inside a function is itself pipeline output, so a function
# that both prints and `return`s hands back an array — and `$drift += ` on an
# array throws op_Addition. The counter is script-scoped for that reason.
function Sync-One($src, $dst, $label, $projName) {
    if (-not (Test-Path $dst)) {
        $state = 'MISSING'
    } elseif ((Get-FileHash $src).Hash -eq (Get-FileHash $dst).Hash) {
        return
    } else {
        $state = 'DRIFT'
    }
    $script:drift++
    if ($Apply) {
        New-Item -ItemType Directory -Force (Split-Path $dst) | Out-Null
        Copy-Item $src $dst -Force
        "{0,-28} {1,-8} {2} -> synced" -f $label, $projName, $state
    } else {
        "{0,-28} {1,-8} {2}" -f $label, $projName, $state
    }
}

# Sync EVERY file in each skill folder, not just SKILL.md. brand.css and
# skins.py live beside it and are just as canonical; when only SKILL.md was
# synced they drifted silently, which is how one project's palette diverged
# from the seed without anything reporting it.
foreach ($skillDir in Get-ChildItem $Kit -Directory | Where-Object { $_.Name -notin $WorkspaceScoped }) {
    # Extension allow-list: a stray file in a kit folder (an editor backup, a
    # crash dump) must not fan itself out into five repos.
    foreach ($file in Get-ChildItem $skillDir.FullName -File |
             Where-Object { $_.Extension -in '.md', '.css', '.py', '.js', '.json' }) {
        foreach ($proj in $Projects) {
            $projName = Split-Path $proj.Path -Leaf
            $dst = Join-Path $proj.Path ".claude\skills\$($skillDir.Name)\$($file.Name)"
            Sync-One $file.FullName $dst "$($skillDir.Name)/$($file.Name)" $projName
        }
    }
}

# brand.css is also a served ASSET, not only skill documentation. It is
# generated and byte-identical everywhere, so a hash mismatch here is real drift
# rather than a project's legitimate skin choice — a project picks its skin with
# one data-skin attribute in its HTML, never by editing this file.
$BrandSrc = Join-Path $Kit 'brand-visuals\brand.css'
if (Test-Path $BrandSrc) {
    foreach ($proj in $Projects | Where-Object { $_.Brand }) {
        $projName = Split-Path $proj.Path -Leaf
        $dst = Join-Path $proj.Path $proj.Brand
        Sync-One $BrandSrc $dst "brand.css (asset)" $projName
    }
}

if ($drift -eq 0) { 'All project skills in sync with kit.' }
elseif (-not $Apply) { "`n$drift out of sync. Diff any DRIFT before running with -Apply (a project copy may be ahead of the kit)." }
