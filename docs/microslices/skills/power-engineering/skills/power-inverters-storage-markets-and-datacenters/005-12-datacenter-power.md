---
id: skill-12-datacenter-power-5f6143729d
purpose: 12 datacenter power
source: src/vibey_tools/skills/plugins/power-engineering/skills/power-inverters-storage-markets-and-datacenters/SKILL.md
requires: ["skill-11-writing-grid-software-9ca191716a"]
links: []
---

## §12. Datacenter Power

**⚠️ The part of this document most software engineers will actually touch — and the
industry has crossed a threshold where compute demand is now a first-order power system
problem** (§15.2 → `power-reference`).

### 12.1 The facility
```
Utility feed → transformer → switchgear → UPS → PDU → rack PDU → PSU → server
                     ↕                      ↕
                  generator             battery/flywheel
```
**Redundancy notation**: **N** (no redundancy), **N+1**, **2N** (⚠️ **fully duplicated**),
**2N+1**. **Tier I–IV** (Uptime Institute) — ⚠️ **Tier III is concurrently maintainable,
Tier IV is fault tolerant, and the distinction is whether a single failure during
maintenance takes you down.**

**UPS topologies**: double-conversion (⚠️ **best isolation, worst efficiency**), line-
interactive, and **eco/multi-mode** which bypasses conversion when input is clean.
**Generators** for extended outages (⚠️ **and the fuel contract is the real constraint,
not the generator**).

**⚠️ PUE (Power Usage Effectiveness)** = total facility power / IT equipment power.
**1.0 is perfect; hyperscale runs near 1.1; older enterprise 1.5–2.0.**
> **⚠️ GOTCHA — PUE measures facility overhead, not useful work.** ⚠️ **A facility at
> PUE 1.05 running inefficient inference wastes more energy per useful output than a
> facility at higher PUE running efficient workloads.** **PUE cannot see software
> efficiency at all**, which is why "tokens per watt" style metrics are the ones that
> matter to the people reading this. **Optimizing PUE while ignoring compute efficiency
> is optimizing the denominator you don't control.**

### 12.2 What software engineers control
**⚠️ Rack density is the current design driver** — modern AI racks reach **~140 kW**,
against a traditional ~5–15 kW, which is why **liquid cooling** moved from exotic to
standard. **⚠️ Air cooling runs out well below current GPU rack densities.**

**Levers that are actually software decisions:**
- **⚠️ Utilization.** An idle server draws a large fraction of peak. **Consolidation and
  autoscaling are power engineering.**
- **Efficiency per unit of work** — model choice, quantization, batching, caching.
  ⚠️ **The largest lever, and invisible to every facility metric.**
- **Carbon-aware scheduling** — ⚠️ **shift flexible work in time or geography toward
  low-carbon grid conditions.** Real, and limited to genuinely deferrable workloads.
- **⚠️ Demand flexibility** — and this is now a grid-interface question, not just an
  internal one (§15.2 → `power-reference`).
