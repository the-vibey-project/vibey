---
id: skill-10-markets-and-dispatch-585a2594d2
purpose: 10 markets and dispatch
source: src/vibey_tools/skills/plugins/power-engineering/skills/power-inverters-storage-markets-and-datacenters/SKILL.md
requires: ["skill-9-storage-527b705108"]
links: ["skill-11-writing-grid-software-9ca191716a"]
---

## §10. Markets and Dispatch

**Unit commitment** — ⚠️ **which units to turn on over the next day, a mixed-integer
program with minimum up/down times and startup costs.**
**Economic dispatch** — how much from each committed unit, continuously.
**Optimal power flow (OPF)** — ⚠️ **dispatch subject to the physical network constraints of
§4.1 → `power-system-analysis-and-protection`.** **AC OPF is non-convex and hard; DC OPF is what most markets actually clear on.**

**LMP (locational marginal price)** decomposes into **energy + congestion + losses** —
⚠️ **which is why prices differ between buses, and why congestion is visible as a price
signal rather than only as an engineering limit.** **Negative prices occur** when
must-run generation and inflexible renewables exceed load.

**Market structure**: day-ahead and real-time, **ancillary services** (regulation, spinning
and non-spinning reserve, voltage support, black start — ⚠️ **and increasingly inertia,
§8.2**), and capacity markets.

**⚠️ For a software engineer, the notable property**: this is a **large-scale optimization
running on a schedule with hard deadlines and real money attached.** ⚠️ **A market
clearing that doesn't converge in time is an operational emergency, not a failed job.**

---
