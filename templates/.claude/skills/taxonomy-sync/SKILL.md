---
name: taxonomy-sync
description: Use in a project owning an "ecosystem canvas" / L1-L3 process taxonomy (a src/core/taxonomy.py with a PROCESS_NODES forest) when asked to sync the taxonomy, reconcile with the master, promote processes upward, or check taxonomy drift — and before shipping any new sector/L2/L3 node in a fork.
---

# SKILL: taxonomy-sync

Trigger when working in a project that owns an "ecosystem canvas" / L1–L3 process
taxonomy (a `src/core/taxonomy.py` with a `PROCESS_NODES` forest) and the user
asks to "sync the taxonomy", "reconcile with the master", "promote these
processes to the master", "check taxonomy drift", or whenever a fork has added or
changed process nodes that should flow back into the master superset. Also fire
this before shipping a new sector/L2/L3 node in any fork, so the master stays the
canonical superset.

## The master rule (read this first)

`python/mktdb` is the **master superset** of the process taxonomy. Every other
project (e.g. `zp_scm`) is a **scoped fork** — a subset of the master, possibly
renamed for its audience, possibly deeper in one area. The invariant:

> Every process node that exists in *any* fork must also exist in mktdb's
> `PROCESS_NODES` (held at full L1/L2/L3 depth). Forks may omit master nodes and
> may rename sectors/markets, but they must not hold a node the master lacks.

Because the data model only supports three levels (L1/L2/L3), a fork that grows a
richer area than the master's placement can hold (e.g. an agentic L3 that would
become an unsupported L4) is the signal to **promote that area to its own sector**
in the master — not to flatten it. (This is exactly how the `distribution` sector
came to exist in mktdb.)

## Node identity (how the diff aligns)

A node is identified by its **path**: `sector_id` → L1 name → L2 name → L3 name.
Sync aligns on this path. Renames of a sector between master and a fork
(`hc_delivery` "Healthcare Delivery & Payers" ↔ "Customers & Channels") are
expected — align on `sector_id`, not display name. The comparable fields on a
matched node are: `ai_inflection`, `ai_tier`, `icon`, `live_url_key`, and the
`accounts` list.

## Workflow (report, never auto-apply)

1. **Locate both taxonomies.** The local fork's `src/core/taxonomy.py`
   `PROCESS_NODES`, and the master at `python/mktdb/src/core/taxonomy.py`
   (relative to the workspace root; adjust if the workspace layout differs).

2. **Run the diff.** If the project ships the helper (mktdb does — see below),
   use it for a deterministic result rather than eyeballing:
   ```bash
   uv run python -m src.utils.taxonomy_diff --against ../mktdb/src/core/taxonomy.py --json
   ```
   Otherwise walk both `PROCESS_NODES` forests by path and build the three
   buckets yourself.

3. **Report three buckets:**
   - **Promote up** — nodes in the fork but *not* in the master. These are
     candidates to add to mktdb so it stays the superset. For each, say where it
     lands in the master (existing sector, or a new sector if depth demands it).
   - **Subset (expected)** — master nodes absent from the fork. Normal; a fork is
     a scoped view. List counts only, not every node, unless asked.
   - **Drift** — same path, different `ai_inflection` / `ai_tier` / `icon` /
     `live_url_key`. Show the field-level delta. Decide per case which side is
     canonical (usually the master, unless the fork deliberately refined it).

4. **Propose edits, do not apply them.** Present the promote-up and drift
   reconciliations as concrete taxonomy edits (which sector block, which parent,
   what `ai_tier`). Master promotions are **hand-confirmed** — wait for the user
   before editing `mktdb/src/core/taxonomy.py`.

5. **After any master edit**, follow through in mktdb: copy any new icons into
   `mktdb/static/img/` (use the `find-icon` skill), reseed a temp DB and run the
   integrity check, regenerate the canvas, and update the mktdb tests + PROGRESS.

## Guardrails

- **`live_url_key` is fork-local config, not master data.** The key may live on a
  master node, but the URL it resolves to (`config.yml` → `external_url`) points
  at a specific fork's deployed demo. Never copy a fork's `external_url` values
  into the master; sync the key, not the URL.
- **Never delete master nodes** to match a fork — the master is a superset by
  definition. A node the fork dropped stays in the master.
- **Additive edits only** on the master taxonomy without explicit sign-off:
  adding a node or refining a note is safe; renaming/removing a node ripples into
  `ProcessNodeCompany` mappings, the canvas, and tests.
- **Reseed before trusting the diff** if either side's DB is stale — the source
  of truth is `taxonomy.py`, but the integrity checker reads the seeded DB.
