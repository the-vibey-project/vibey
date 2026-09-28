---
id: skill-11-writing-grid-software-9ca191716a
purpose: 11 writing grid software
source: src/vibey_tools/skills/plugins/power-engineering/skills/power-inverters-storage-markets-and-datacenters/SKILL.md
requires: ["skill-10-markets-and-dispatch-585a2594d2"]
links: ["skill-12-datacenter-power-5f6143729d"]
---

## §11. Writing Grid Software

### 11.1 The character of the domain
**⚠️ Timescales span twelve orders of magnitude**, and which one you're in dictates
everything:
```
µs–ms      protection, GOOSE, sampled values     ⚠️ hard real-time, safety-critical
ms–s       inverter control, AGC
s–min      SCADA, state estimation
min–h      dispatch, markets
h–yr       planning
```
**⚠️ Reliability expectations are extreme**: control-room systems target very high
availability, field devices run for 20+ years, and **the cost of a wrong answer is
measured in outages and lives.** **This is much closer to avionics and automotive
practice (see those references) than to web engineering.**

### 11.2 ⚠️ Security — OT is not IT
**NERC CIP** in North America is a mandatory, auditable, **fineable** standard covering
asset identification, security management, personnel and training, electronic security
perimeters, physical security, system security management, incident response, recovery,
configuration change management, and supply chain risk.
**⚠️ The OT/IT differences that catch software engineers out:**
- **Availability outranks confidentiality** — ⚠️ **the reverse of most IT threat models.**
- **⚠️ You cannot patch on Tuesday.** Devices may not be patchable at all, and taking them
  out of service requires a switching order.
- **⚠️ Air gaps are largely mythical in practice** — segmentation, unidirectional gateways
  and rigorous perimeter control are the real controls.
- **Legacy protocols with no authentication** (§7 → `power-scada-ems-and-protocols`) mean **network position is
  authorization**, which is exactly why segmentation carries the load.
- ⚠️ **Ukraine 2015/2016 and Industroyer/CRASHOVERRIDE are the reference cases** — grid
  malware that spoke the protocols in §7 → `power-scada-ems-and-protocols` natively.

### 11.3 Practice
**Testing**: simulation against a network model, **hardware-in-the-loop** with real relays
(⚠️ **real-time digital simulators are standard for protection validation**), replay of
recorded disturbances, and **model validation against actual event data** — ⚠️ **which is
where a lot of models are found wanting after a real disturbance.**
**Tools**: **PSS/E, PowerWorld, PSCAD/EMTP** (⚠️ **electromagnetic transient simulation —
required for inverter control studies, because phasor-domain tools miss the fast
dynamics**), **OpenDSS** and **GridLAB-D** (distribution), **PYPOWER, pandapower, PowerModels.jl,
MATPOWER** (⚠️ **the open research stack**), **GridPACK**, **Grid2Op** for RL work.
**Data**: CIM (§7 → `power-scada-ems-and-protocols`), historians, PMU archives, and ⚠️ **an obsession with time
synchronization — PTP/IEEE 1588 and GPS, because sequence-of-events analysis after a
disturbance depends entirely on trustworthy timestamps.**

---
