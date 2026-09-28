---
id: skill-6-scada-ems-and-dms-4f5de13ad1
purpose: 6 scada ems and dms
source: src/vibey_tools/skills/plugins/power-engineering/skills/power-scada-ems-and-protocols/SKILL.md
requires: []
links: ["skill-7-protocols-e1cb2f0eac"]
---

## §6. SCADA, EMS, and DMS

```
Field:  sensors, CTs/VTs, IEDs, relays, RTUs
   ↓ (§7 protocols)
SCADA:  acquisition, alarms, supervisory control, historian
   ↓
EMS (transmission):  state estimation, contingency analysis, OPF, AGC, dispatch
DMS (distribution):  fault location/isolation/restoration (FLISR), volt/VAr,
                     outage management, DERMS
   ↓
Markets (§10), planning, asset management
```
**⚠️ Contingency analysis is the control room's core loop**: continuously simulate
**"what if this element fails?"** across a large list, and confirm the system stays within
limits. **The `N−1` criterion means operating so that any single failure is survivable** —
⚠️ **so the grid is deliberately run below its physical capability, always.**

**⚠️ The operator is the user, and the design constraints are unusual**: alarm floods
during a real event are a documented contributor to blackout escalation; the system must
degrade legibly; and ⚠️ **the software's job during a crisis is to reduce the number of
things a human must decide, not to present more information.**

---
