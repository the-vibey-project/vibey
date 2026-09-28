---
id: skill-11-heat-pumps-c81b366dd9
purpose: 11 heat pumps
source: src/vibey_tools/skills/plugins/refrigeration-ac-climate-control-food-water/skills/hvacr-load-calculation-air-humidity-and-heat-pumps/SKILL.md
requires: ["skill-10-ventilation-and-indoor-air-quality-e621a7f43d"]
links: ["skill-12-controls-49003061bf"]
---

## §11. Heat Pumps

**⚠️ A refrigeration cycle with a reversing valve — and the single most important point is
that COP above 1 is normal and does not violate anything** (see a thermo reference):
**you're moving heat, not making it.**
```
⚠️ COP falls as the temperature LIFT rises — which is why air-source
   performance degrades in cold weather
⚠️ COLD-CLIMATE models use vapour injection, variable speed and better
   controls; ⚠️ modern units maintain useful capacity well below 0°C,
   which is a genuine change from older equipment
⚠️ DEFROST  outdoor coil frosts below freezing; the unit periodically
   REVERSES to melt it. ⚠️ The steam and the temporary cold air are
   normal and are constantly misdiagnosed as faults
⚠️ BALANCE POINT  where capacity meets load; below it, supplementary heat
   ⚠️ RESISTANCE BACKUP has COP 1 — every hour it runs erases the savings.
   Controls that call it unnecessarily are the main cause of
   disappointing heat-pump bills
GROUND-SOURCE  ⚠️ much smaller lift, higher COP, high capital cost
```
**⚠️ The efficiency metrics** (SEER2, HSPF2, EER, COP) ⚠️ **are seasonal averages under
test conditions, and real performance depends heavily on installation quality, charge
(§5 → `hvacr-cycle-components-refrigerants-and-diagnosis`), airflow (§8) and controls.**

---
