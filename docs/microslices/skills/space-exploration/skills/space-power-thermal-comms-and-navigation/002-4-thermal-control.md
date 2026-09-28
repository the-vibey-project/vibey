---
id: skill-4-thermal-control-f8b3d24d90
purpose: 4 thermal control
source: src/vibey_tools/skills/plugins/space-exploration/skills/space-power-thermal-comms-and-navigation/SKILL.md
requires: ["skill-3-power-82c4a5fb42"]
links: ["skill-5-communications-95cae00d64"]
---

## §4. Thermal Control

**[DURABLE] In vacuum there is no convection.** Heat moves by conduction and radiation
only, and radiation is the only path off the vehicle:
```
Q_rad = εσA(T⁴ − T_sink⁴)
```
**⚠️ The `T⁴` is brutal**: rejecting heat from a cold radiator requires enormous area.
A radiator at 300 K rejects ~460 W/m² at best; at 200 K, ~91 W/m².

**Equilibrium temperature** from absorbed sunlight:
```
T_eq = [ (α/ε) · S · A_proj / (σ A_rad) ]^(1/4)
```
⚠️ **The `α/ε` ratio — solar absorptivity over infrared emissivity — is the primary
design knob**, and it's why thermal control is largely a coatings problem. White paint
(`α/ε ≈ 0.2`) runs cold; polished metal runs hot; **second-surface mirrors and OSRs**
give very low `α/ε` for radiators.

**Passive**: **MLI blankets** (⚠️ **10–30 layers of aluminized Mylar; effective emissivity
~0.01–0.03 — the single most effective thermal component on most spacecraft**), coatings,
thermal isolators, **heat pipes** (⚠️ **capillary two-phase transport, no moving parts,
very high effective conductivity**), thermal mass.

**Active**: electric heaters (⚠️ **often the largest steady power draw on an outer-planet
spacecraft**), louvres, pumped fluid loops, **cryocoolers** for IR detectors.

**⚠️ The extremes are what break designs**: **JWST** needs its instruments below ~40 K,
achieved with a tennis-court-sized sunshield giving ~300 K of gradient across five layers;
**Parker Solar Probe** survives ~1,400 °C on a carbon-composite shield while the bus stays
near room temperature; **lunar surface** swings ~120 °C to −170 °C, and ⚠️ **permanently
shadowed craters sit near 25–40 K**, which is colder than Pluto's surface and a genuine
materials problem.

---
