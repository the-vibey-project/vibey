---
id: skill-9-turbomachinery-engine-cycles-and-cooling-ca34e541a4
purpose: 9 turbomachinery engine cycles and cooling
source: src/vibey_tools/skills/plugins/military-space-rockets-and-fusion/skills/endeavour-rocket-equation-nozzles-engines-and-propellants/SKILL.md
requires: ["skill-8-nozzle-thermodynamics-the-c-c-f-factorization-and-the-combustion-chamber-eaf6cdcfc6"]
links: ["skill-10-propellants-and-density-impulse-5ffc757a7d"]
---

## §9 Turbomachinery, engine cycles, and cooling

Turbopumps **decouple tank pressure** (~0.2–0.4 MPa, mostly for NPSH and structural stability) **from
chamber pressure** (7–30 MPa). Pump power:

    P = ṁ · Δp / (ρ · η)

The numbers are startling — the **SSME's high-pressure fuel turbopump delivers about 70 MW from a
unit you can lift**. **Cavitation** is the recurring failure; **inducers** (axial pre-stages) are
fitted to raise suction performance and allow lower tank pressures.

### Engine cycles

| Cycle | Turbine drive gas | Turbine exhaust | Isp penalty | p_c ceiling |
|---|---|---|---|---|
| Pressure-fed | — | — | none | tank-limited, ~2–3 MPa |
| Gas generator | Separate preburner, fuel-rich | Dumped overboard | 1–3% | ~10–12 MPa |
| Expander | Fuel heated in cooling jacket | To chamber | ~0 | heat-transfer-limited |
| Staged combustion (ORSC/FRSC) | Preburner, oxidizer- or fuel-rich | Into chamber | ~0 | 20–26 MPa |
| Full-flow staged | Two preburners, both flows | Both into chamber | ~0 | 30+ MPa |

> **THE EXPANDER CYCLE'S FUNDAMENTAL LIMIT IS GEOMETRIC.** Available heat scales with chamber surface
> area (∝ r²) while required power scales with mass flow (∝ r³ roughly). Beyond **~250 kN** there is
> not enough wall heat to drive the pump. This is a **hard physical ceiling, not an engineering
> shortfall** — hence RL10-class engines only.

**Full-flow staged combustion's real advantage is not just Isp.** Both turbines run on gas that has
already passed through a preburner, so **turbine inlet temperatures are lower for a given chamber
pressure**, and **no fuel-oxidizer interpropellant seal is needed** — each turbopump sees only its own
propellant. That seal is a classic failure point; eliminating it is a **reliability argument as much
as a performance one**.

### Cooling and heat transfer

Chamber wall heat flux is **the highest sustained flux in routine engineering** — typically **10–160
MW/m² at the throat**. For comparison, **a domestic hob is ~0.05 MW/m².**

The **Bartz correlation** shows **h_g ∝ p_c^0.8** — raising chamber pressure raises heat flux nearly
proportionally, which is **the real constraint on high-p_c engines, not structural strength**.

| Method | How it works | What it costs |
|---|---|---|
| **Regenerative** | Propellant through milled channels or brazed tubes before injection | Pressure drop (pump work), **not** energy — the heat is returned to the chamber |
| **Film / curtain** | A fuel-rich boundary layer at the wall | Isp directly (that propellant burns poorly), typically **1–3%** |
| **Ablative** | Sacrificial charring liner | Simple, single-use-ish, mass-heavy |
| **Radiative** | Nozzle extensions where q is low | Niobium or carbon-carbon at **1,300–1,800 K** |
