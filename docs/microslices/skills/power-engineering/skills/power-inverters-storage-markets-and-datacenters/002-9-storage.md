---
id: skill-9-storage-527b705108
purpose: 9 storage
source: src/vibey_tools/skills/plugins/power-engineering/skills/power-inverters-storage-markets-and-datacenters/SKILL.md
requires: ["skill-8-inverters-renewables-and-the-inertia-problem-fdb0fa2f76"]
links: ["skill-10-markets-and-dispatch-585a2594d2"]
---

## §9. Storage

| Technology | Duration | ⚠️ Notes |
|---|---|---|
| **Li-ion BESS** | ⚠️ **~1–4 h** | Dominant; fast, and duration-limited |
| **Pumped hydro** | 8–24 h+ | ⚠️ **~95% of world storage capacity; geography-limited** |
| **Flow batteries** | 4–12 h | Decoupled power and energy |
| **Compressed air, thermal** | Long | Niche |
| **Hydrogen** | Seasonal | ⚠️ **Poor round-trip efficiency** |

**⚠️ Batteries are inverter-interfaced (§8), which means their grid services are a software
question**: frequency regulation (⚠️ **the highest-value early application, because they're
faster than any generator**), energy arbitrage, capacity, **synthetic inertia via GFM
control**, black start, and **T&D deferral.**

**⚠️ The one that matters for software**: **state of charge is a hard constraint that
couples decisions across time.** A battery dispatched greedily for regulation revenue can
be empty when the capacity obligation lands. **Every storage optimization is a temporal
one, and cycling degrades the asset — so the objective function has to include
degradation cost or it will destroy the battery profitably.**

---
