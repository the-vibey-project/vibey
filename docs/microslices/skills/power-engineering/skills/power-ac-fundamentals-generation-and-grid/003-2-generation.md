---
id: skill-2-generation-368d484124
purpose: 2 generation
source: src/vibey_tools/skills/plugins/power-engineering/skills/power-ac-fundamentals-generation-and-grid/SKILL.md
requires: ["skill-1-ac-power-fundamentals-de6d548b4f"]
links: ["skill-3-transmission-and-distribution-c5981012e8"]
---

## §2. Generation

| Type | Character | ⚠️ Grid role |
|---|---|---|
| **Coal / gas steam** | Synchronous, slow ramp | ⚠️ **Provides inertia; being retired** |
| **Gas turbine (CT/CCGT)** | Synchronous, fast ramp | ⚠️ **The flexibility workhorse** |
| **Nuclear** | Synchronous, baseload | Inertia; economically inflexible |
| **Hydro** | ⚠️ **Synchronous, very fast, storable** | Inertia, black start, regulation |
| **Wind** | ⚠️ **Inverter-interfaced** | Variable; §8 → `power-inverters-storage-markets-and-datacenters` |
| **Solar PV** | ⚠️ **Inverter-interfaced, no rotating mass** | Variable; §8 → `power-inverters-storage-markets-and-datacenters` |
| **Battery** | ⚠️ **Inverter-interfaced, bidirectional** | Fast response; §9 → `power-inverters-storage-markets-and-datacenters` |

**⚠️ The distinction that matters more than fuel type is synchronous vs inverter-interfaced.**
A synchronous machine is **electromechanically coupled to grid frequency** — its physics
resists change and it contributes fault current and inertia automatically. **An inverter
does whatever its control software says**, which is both the opportunity and the problem
(§8 → `power-inverters-storage-markets-and-datacenters`).

**Black start** — ⚠️ **restarting a dead grid requires units that can start without
external power** (hydro, some diesel/gas). **A grid with no black-start capability cannot
recover from a full collapse**, which is why it's a contracted service.

---
