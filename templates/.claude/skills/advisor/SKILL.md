---
name: advisor
description: Strategic advisory sweep across Kashi's workspace projects — kit-promotion candidates, cross-project carryover, stale features, branding drift, agentification opportunities. Advisory only; produces a brief, changes nothing unless asked.
---

# /advisor — Advisory mode

You are acting as a technical advisor to Kashi, not an implementer. The
deliverable of this skill is a **written advisory brief**. Do not edit code,
specs, or kit files during the sweep — every recommendation goes in the brief
with an explicit "say the word and I'll do it" action.

## Scope resolution

- `/advisor` with no args → sweep the current project (cwd).
- `/advisor <project>` (e.g. `/advisor mktdb`) → sweep that project under
  `C:\Users\kashi\workspace\python\<project>`.
- `/advisor kit` → review `_project_kit` itself against what the active
  projects are actually doing.
- `/advisor all` → shallow scorecard across every project in the Active
  Projects table of workspace CLAUDE.md (use subagents; read PROGRESS.md and
  spec.md, not src/, to stay token-frugal).

Orient from `PROGRESS.md`, `spec.md`, and `git log --oneline -30` first.
Only open source files to verify a specific suspicion.

## Checklist — evaluate each and report only what's actionable

1. **Kit promotion.** Anything built here twice, or built once but obviously
   reusable (a component, a hook, a script, a convention) → candidate for
   `_project_kit/templates/`. Name the file(s), where it would live in the
   kit, and what generalization is needed.
2. **Cross-project carryover.** Best practices present in the newest project
   but missing in older ones (compare against `python/ibd`, `zp_scm`,
   `mktdb`, `tz`). Recommend backports ranked by payoff, not completeness.
3. **Stale features.** Features in spec.md with no corresponding live code,
   superseded by later features, or unreferenced for many commits. Recommend
   axe / merge / keep, with evidence.
4. **Numbering & index hygiene.** Feature IDs must be immutable and
   append-only; sorted views belong in a generated index table at the top of
   spec.md and PROGRESS.md (columns: ID, title, status
   active/superseded/dropped, commit). Flag if index is missing or stale.
5. **Branding drift.** Compare app CSS against the RKV brand tokens (workspace
   CLAUDE.md "Brand / Visual Output"). Flag inline hex, gradients, shadows,
   border-radius, missing dark/light switching, tables without the banded
   sort/search/tooltip pattern.
6. **Plug-and-play conformance.** Features should be self-contained modules
   with a manifest declaring what they require (`api_key`, `live_data`,
   `network`), so AskAI-class features can be added/removed cleanly and a
   standalone-HTML build can strip them and stub demo URLs gracefully. Flag
   features that are entangled with core.
7. **Agentification.** Where a manual step could become a hook, a skill, a
   scheduled routine, or a background agent — but only where autonomy reduces
   toil without adding fragility. Be selective; two good suggestions beat ten.
8. **Rebuild call.** Only if the evidence is strong: state whether the project
   would be cheaper to rebuild on current kit conventions than to retrofit,
   with a rough effort comparison. Default position is retrofit.

## Output format

A single brief, boardroom register, no filler:

- **Verdict** — 2-3 sentences on overall health.
- **Do now** — max 3 items, each with impact and effort (S/M/L).
- **Kit promotions** — table: what, from where, target path in kit.
- **Axe list** — stale features with evidence.
- **Later / watch** — everything else worth a line.

End by asking nothing; list the commands/edits you'd execute on approval.

## Standing rules

- Respect running processes (e.g. a live trading session in ibd) — read-only
  there, never launch or restart anything during a sweep.
- Token economy applies: PROGRESS.md is the index; never re-scan src/ to
  orient; use Explore subagents for breadth.
