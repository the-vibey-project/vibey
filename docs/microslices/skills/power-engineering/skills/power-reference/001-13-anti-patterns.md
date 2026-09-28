---
id: skill-13-anti-patterns-5ac6b1afb4
purpose: 13 anti patterns
source: src/vibey_tools/skills/plugins/power-engineering/skills/power-reference/SKILL.md
requires: []
links: ["skill-14-numbers-ff99caf5fd"]
---

## §13. Anti-Patterns

| Anti-pattern | Why |
|---|---|
| Treating reactive power as waste | ⚠️ **It holds voltage up. The question is where it's sourced** (§1.2 → `power-ac-fundamentals-generation-and-grid`) |
| Assuming voltage is a system-wide quantity | ⚠️ **Voltage is local; frequency is global** (§1.2 → `power-ac-fundamentals-generation-and-grid`) |
| Undersized neutral in a nonlinear-load facility | ⚠️ **Triplen harmonics add rather than cancel** (§1.3 → `power-ac-fundamentals-generation-and-grid`) |
| Ignoring per-unit conventions | Every number will confuse you (§1.5 → `power-ac-fundamentals-generation-and-grid`) |
| Relaxing tolerance when power flow won't converge | ⚠️ **Non-convergence may mean genuine infeasibility** (§4.1 → `power-system-analysis-and-protection`) |
| Acting on raw telemetry rather than the state estimate | That's what state estimation is for (§4.2 → `power-system-analysis-and-protection`) |
| Overcurrent protection settings assuming synchronous fault current | ⚠️ **Inverters supply ~1.1–2× rated. The relay may not see it** (§5 → `power-system-analysis-and-protection`, §8.1 → `power-inverters-storage-markets-and-datacenters`) |
| Treating GFM inverters as a solved replacement for inertia | ⚠️ **~12% of UK contracted inertia by 2026; the rest is rotating mass** (§8.2 → `power-inverters-storage-markets-and-datacenters`) |
| Assuming an air gap protects OT | ⚠️ **It's mostly mythical. Segment properly** (§11.2 → `power-inverters-storage-markets-and-datacenters`) |
| Applying IT patch cadence to OT | ⚠️ **Availability outranks confidentiality here** (§11.2 → `power-inverters-storage-markets-and-datacenters`) |
| Assuming a protocol authenticates the sender | ⚠️ **Most in §7 → `power-scada-ems-and-protocols` don't** (§7 → `power-scada-ems-and-protocols`) |
| Phasor-domain simulation for inverter control studies | ⚠️ **Misses the fast dynamics. Use EMT** (§11.3 → `power-inverters-storage-markets-and-datacenters`) |
| Sloppy time synchronization | ⚠️ **Sequence-of-events analysis becomes worthless** (§11.3 → `power-inverters-storage-markets-and-datacenters`) |
| Alarm design that floods during real events | Documented blackout escalation factor (§6 → `power-scada-ems-and-protocols`) |
| Greedy battery dispatch ignoring state of charge | ⚠️ **Empty when the obligation lands** (§9 → `power-inverters-storage-markets-and-datacenters`) |
| Storage optimization without degradation cost | Destroys the asset profitably (§9 → `power-inverters-storage-markets-and-datacenters`) |
| Optimizing PUE while ignoring workload efficiency | ⚠️ **PUE cannot see software at all** (§12.1 → `power-inverters-storage-markets-and-datacenters`) |
| Air cooling at modern AI rack density | ⚠️ **It doesn't work above ~40 kW/rack** (§12.2 → `power-inverters-storage-markets-and-datacenters`) |
| Assuming grid capacity is available on your timeline | ⚠️ **4–10 year interconnection queues** (§15.2) |

---
