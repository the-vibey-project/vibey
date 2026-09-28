---
id: skill-15-dram-internals-509a82c954
purpose: 15 dram internals
source: src/vibey_tools/skills/plugins/microarchitecture-and-memory-systems/skills/uarch-dram-memory-controllers-power-and-security/SKILL.md
requires: []
links: ["skill-16-memory-controllers-f61118b65c"]
---

## §15. ⚠️ DRAM Internals

> **⚠️ The component whose behaviour is least understood by the people tuning it.**
```
⚠️ THE STRUCTURE  ⚠️ cell (one transistor + one capacitor) →
   row (page) → bank → bank group → rank → channel → DIMM
⚠️ ⚠️ ACCESS IS A THREE-STEP SEQUENCE, and this explains all the
   timing numbers
   ⚠️ 1. ACTIVATE  ⚠️ copy an entire ROW into the row buffer —
      ⚠️ this is DESTRUCTIVE (reading the capacitors drains them)
   ⚠️ 2. READ/WRITE from the row buffer — ⚠️ fast if the row is
      already open (ROW HIT), slow if not
   ⚠️ 3. PRECHARGE  ⚠️ write the row back and prepare for the next
⚠️ THE TIMINGS people quote  ⚠️ CL (CAS latency) · tRCD (activate
   to read) · tRP (precharge) · tRAS (minimum row active)
   ⚠️ THE HEADLINE "CL16" IS ONLY THE ROW-HIT CASE. ⚠️ A row miss
   costs tRP + tRCD + CL — roughly triple
⚠️ ⚠️ ACTUAL LATENCY IN NANOSECONDS = CL ÷ (data rate ÷ 2) × 1000.
   ⚠️ Higher-MT/s memory usually has higher CL, so real latency
   has barely improved across DDR generations — ⚠️ BANDWIDTH is
   what improved
⚠️ REFRESH  ⚠️ capacitors leak, so every row must be refreshed
   periodically (⚠️ typically every 64 ms). ⚠️ Refresh consumes
   bandwidth and blocks access, and the cost RISES with density
⚠️ BANK PARALLELISM  ⚠️ multiple banks let one activate overlap
   another's transfer — the memory controller's main lever (§16)
⚠️ ⚠️ ROWHAMMER  ⚠️ repeatedly activating a row disturbs charge in
   PHYSICALLY ADJACENT rows and can flip their bits — ⚠️ a
   reliability property that became a security vulnerability,
   and mitigations (TRR, on-die ECC) have repeatedly been bypassed
```

---
