---
name: mktdb-as-pattern-library
description: User treats mktdb as the gold-standard pattern library for insead; prefers YAML over JSON; wants runtime model/search switchboards and CxO-grade KPI framing
metadata: 
  node_type: memory
  type: user
  originSessionId: 1324eac6-670f-4c0e-a4f7-dc44bfd9a306
---

The user considers `C:\Users\kashi\python\mktdb` their reference for how
features should feel: the Ecosystem Canvas (L1/L2/L3 process taxonomy),
styled-xlsx CRUD round-trips (`excel_io.py`), and the Ask AI switchboard
(config.yml + /api/config + Settings tab, provider AND model selectable at
runtime, search provider pluggable — Tavily is "one of the options", never
hardcoded).

**Why:** mktdb shipped well; the user explicitly said "I really like the way
you built the ecosystem in mktdb" and asked for the same provisions in insead.

**How to apply:** when specing/building similar capabilities, read the
corresponding mktdb feature (spec.md Features 8, 13, 19) as the pattern first.
Prefer YAML over JSON for anything humans author ("friendlier"). Frame
analytics for a board audience — e.g. KPI value trees consolidating processes
into measurable outcomes (EBITDA uplift, market share), with qualitative
weights rather than fabricated numeric precision.
