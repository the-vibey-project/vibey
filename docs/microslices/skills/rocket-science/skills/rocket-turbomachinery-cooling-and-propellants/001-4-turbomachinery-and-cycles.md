---
id: skill-4-turbomachinery-and-cycles-2456b436fc
purpose: 4 turbomachinery and cycles
source: src/vibey_tools/skills/plugins/rocket-science/skills/rocket-turbomachinery-cooling-and-propellants/SKILL.md
requires: []
links: ["skill-5-heat-transfer-and-cooling-8143ab0d31"]
---

## §4. Turbomachinery and Cycles

### 4.1 Why pumps

**[DURABLE]** Pressure-fed systems need tank pressure > chamber pressure. Tank mass scales
with `p·V`, so for a large stage at `p_c` = 10 MPa the tanks would be absurd.
**Turbopumps decouple tank pressure (~0.2–0.4 MPa, mostly for NPSH and structural
stability) from chamber pressure (7–30 MPa).**

**Pump power**: `P = ṁ · Δp / (ρ · η)`.
⚠️ **The numbers are startling** — the SSME's high-pressure fuel turbopump delivers about
**70 MW** from a unit you can lift. That power density is why turbopumps are the hardest
component in the engine.

**⚠️ Cavitation is the recurring failure**. Required **NPSH** (net positive suction head)
must be met or vapour bubbles form and collapse, destroying the impeller. **Inducers**
(axial pre-stages) are fitted specifically to raise suction performance and allow lower
tank pressures — which saves tank mass.

### 4.2 Cycle thermodynamics compared

| Cycle | Turbine drive gas | Turbine exhaust | Isp penalty | p_c ceiling |
|---|---|---|---|---|
| **Pressure-fed** | — | — | none | ⚠️ tank-limited, ~2–3 MPa |
| **Gas generator** | Separate preburner, fuel-rich | **Dumped overboard** | ⚠️ **1–3%** | ~10–12 MPa |
| **Expander** | Fuel heated in cooling jacket | To chamber | ~0 | ⚠️ **heat-transfer-limited** |
| **Expander bleed** | Same, partial flow | Dumped | small | higher than closed expander |
| **Staged combustion (ORSC/FRSC)** | Preburner, oxidizer- or fuel-rich | **Into chamber** | ~0 | 20–26 MPa |
| **Full-flow staged** | Two preburners, both flows | Both into chamber | ~0 | ⚠️ **30+ MPa** |

**⚠️ The expander cycle's fundamental limit is geometric**: available heat scales with
chamber *surface area* (∝ r²) while required power scales with *mass flow* (∝ r³ roughly).
**Beyond ~250 kN there isn't enough wall heat to drive the pump.** This is a hard physical
ceiling, not an engineering shortfall — hence RL10-class engines only.

**⚠️ Full-flow staged combustion's real advantage isn't just Isp**: both turbines run on
gas that has already passed through a preburner, so **turbine inlet temperatures are lower
for a given chamber pressure**, and **no fuel-oxidizer interpropellant seal is needed**
(each turbopump sees only its own propellant). **That seal is a classic failure point** —
eliminating it is a reliability argument as much as a performance one.

**Oxygen-rich staged combustion** is a **materials problem**: hot, high-pressure oxygen
will burn most metals. Soviet/Russian work on burn-resistant alloys and protective coatings
(ZhS6K, enamel coatings) is what made RD-170/RD-180 possible, and it was a genuine
decades-long capability advantage.

---
