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
#   aidc   — its brand.css is still the TCS-derived theme, and its deck uses 15
#            token names the RKV seed does not define (--surface-elevated,
#            --cta-bg, --shadow-*, --radius-*, --brand-yellow, --status-orange).
#            Overwriting would not re-skin it, it would break it. Migrating aidc
#            onto the registry is its own feature.
#   ibd    — frozen at tag ibd-frozen, read-only; not listed at all
#   zp_scm — archived to zArchive/zp_scm (2026-08-02)
#
# `Ask` is where that project vendors the rkv-ask dock. $null means "do not
# auto-sync ask.js/ask.css/README.md here" — either the project doesn't use
# the dock, or (mktdb) this script's single-directory model doesn't fit it:
#   kite   — has a hand-written dock on its own tokens; it is the UPSTREAM this
#            component was extracted from, so fanning the kit copy in would be
#            backwards. Migrating kite onto the vendored component is its own
#            feature.
#   wheels — vendors the scaffold copy at the REPO ROOT (rkv-ask/), not under
#            static/vendor/, and has not wired the dock into index.html at all.
#            Pointing Ask at static\vendor\rkv-ask made the report claim three
#            MISSING files and would have -Applied a second, unused copy beside
#            the real one. Its README.md and llm_client.py are also AHEAD of the
#            kit. Re-point this when the dock is actually wired, backporting the
#            ahead files to the kit first.
#   mktdb  — DOES have the Ask AI dock (static/js/ask.js), unlike the stale
#            claim this comment used to make — but splits js and css into
#            different directories (static/js/ vs static/css/) rather than
#            co-locating them like ibf's static/vendor/rkv-ask/, so it can't
#            use this script's one-Ask-dir-holds-all-three-files model
#            without extending Sync-One to take separate js/css destinations.
#            Kept manual for now: when ask.js changes in the kit, hand-copy
#            it into mktdb's static/js/ask.js too.
#   aidc   — no Ask AI feature.
$Projects = @(
    @{ Path = 'C:\Users\kashi\workspace\python\wheels'
       Brand = 'static\brand.css';      Ask = $null }
    @{ Path = 'C:\Users\kashi\workspace\python\ibf'
       Brand = 'static\brand.css';      Ask = 'static\vendor\rkv-ask' }
    # rolodex is CLI-only — no port, no served dashboard, so no brand.css asset
    # and no Ask dock. It is listed anyway because it CARRIES kit skills, and an
    # unlisted carrier is exactly how kite drifted for weeks (see above): the
    # skill loop below fans out regardless of Brand/Ask being $null.
    @{ Path = 'C:\Users\kashi\workspace\python\rolodex'
       Brand = $null;                   Ask = $null }
    @{ Path = 'C:\Users\kashi\workspace\python\kite'
       Brand = 'static\brand.css';      Ask = $null }
    @{ Path = 'C:\Users\kashi\workspace\python\mktdb'
       Brand = 'static\css\brand.css';  Ask = $null }
    @{ Path = 'C:\Users\kashi\workspace\python\aidc'
       Brand = $null;                   Ask = $null }
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

# rkv-ask is a served COMPONENT, and until now nothing delivered it after
# scaffold time: new-project.ps1 copies templates/* exactly once, at project
# creation. That is how ibf's copy sat frozen at an Aug-1 snapshot while the kit
# moved on, and it is why the whole "vendored but unused" failure in PATTERNS §1e
# was able to go unnoticed for four features.
#
# ask.js and ask.css are byte-identical everywhere BY DESIGN — §1e forbids
# re-theming by editing the component, so a project maps an --ask-* token layer
# instead. That makes a hash mismatch here real drift, exactly like brand.css.
#
# llm_client.py is deliberately NOT fanned out. It is a starting point to copy
# and adapt ("prune providers to what the project actually needs", per its own
# docstring), not an asset to hold identical — ibf's copy is legitimately
# rewritten async because the kit's is synchronous and calls asyncio.run() inside
# ask(), which raises under a running loop. Hash-checking it would report
# permanent DRIFT on a correct project, and a report that cries wolf gets ignored.
$AskSrc = Join-Path $PSScriptRoot 'templates\rkv-ask'
if (Test-Path $AskSrc) {
    foreach ($file in Get-ChildItem $AskSrc -File |
             Where-Object { $_.Name -in 'ask.js', 'ask.css', 'README.md' }) {
        foreach ($proj in $Projects | Where-Object { $_.Ask }) {
            $projName = Split-Path $proj.Path -Leaf
            $dst = Join-Path $proj.Path (Join-Path $proj.Ask $file.Name)
            Sync-One $file.FullName $dst "rkv-ask/$($file.Name)" $projName
        }
    }
}

if ($drift -eq 0) { 'All project skills in sync with kit.' }
elseif (-not $Apply) { "`n$drift out of sync. Diff any DRIFT before running with -Apply (a project copy may be ahead of the kit)." }
