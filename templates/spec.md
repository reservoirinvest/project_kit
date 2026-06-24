# spec.md

Append a `## Feature N: name` section per feature, in order, at the bottom.
Don't rewrite earlier sections once built — PROGRESS.md is the record of what
shipped. If requirements change, add a new "Feature N revision" section.

**No "Core" section needed.** Claude decides core-vs-feature per feature (rule:
would 2+ features need it?) and reports the call in PROGRESS.md. Just describe
the feature.

Loose template per feature:
- **Goal** — what + why, 1-2 sentences
- **Inputs** — data/config needed
- **Outputs** — what it produces, where
- **First-run vs subsequent-run behavior** — if relevant
- **Source(s)** — external dependencies
- **Open questions** — your uncertainties (Claude flags its own too)

---

<!-- ## Feature 1: name -->
