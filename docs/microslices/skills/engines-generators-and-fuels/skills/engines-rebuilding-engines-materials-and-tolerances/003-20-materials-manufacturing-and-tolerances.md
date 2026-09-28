---
id: skill-20-materials-manufacturing-and-tolerances-f7ed44b9ed
purpose: 20 materials manufacturing and tolerances
source: src/vibey_tools/skills/plugins/engines-generators-and-fuels/skills/engines-rebuilding-engines-materials-and-tolerances/SKILL.md
requires: ["skill-19-engine-management-and-forced-induction-17f5911b32"]
links: []
---

## §20 Materials, manufacturing and tolerances

### Materials for engine components

| Component | Material | Why |
|---|---|---|
| Engine block | Cast iron or aluminium alloy | Iron: strength, wear resistance, damping. Aluminium: weight, thermal conductivity, corrosion resistance. |
| Crankshaft | Forged steel (or cast iron for low stress) | Fatigue strength is critical — the crank sees alternating bending and torsion every revolution. Forging produces favourable grain flow and superior fatigue properties. This is why critical parts are forged, not cast. |
| Connecting rods | Forged steel or powdered metal (some performance rods titanium) | Tensile and fatigue strength; the rod sees alternating tension-compression at high frequency. |
| Pistons | Aluminium alloy (hypereutectic or forged) | Light weight reduces reciprocating mass and inertia forces; good thermal conductivity. Trade-off is high thermal expansion, allowed for in piston-to-cylinder clearance. |
| Valves | Intake: alloy steel. Exhaust: austenitic stainless or Inconel (nimonic) | Exhaust valves see 600–800°C and must resist oxidation, scaling and creep. Sodium-cooled valves (hollow stems filled with sodium transferring heat from head to stem) are used in high-output engines. |
| Turbine blades | Nickel-based superalloys (Inconel, Hastelloy), single-crystal for first stage | Gas turbine first-stage blades see 1400–1600°C gas — above the melting point of the alloy. They survive via internal cooling channels and thermal barrier coatings. Single-crystal blades eliminate grain boundaries, which are creep-initiation sites. |
| Boiler tubes | Carbon steel (low pressure), chromium-molybdenum alloy (high pressure/temperature) | Creep resistance at temperature; corrosion resistance on the fire side and water side. |
| Generator windings | Copper (conductors), electrical steel (core laminations) | Copper for highest conductivity at reasonable cost. Core steel is silicon steel (4% Si) to reduce eddy current losses; laminated and insulated between sheets. |

This table is where the Carnot ceiling stops being thermodynamics and becomes metallurgy: raising T_H
is a **materials** problem (§2 → `engines-thermodynamics-and-the-carnot-ceiling`). Turbine blades tie
to the Brayton cycle (§9 → `engines-otto-diesel-brayton-stirling-and-combined-cycles`) and boiler
tubes to Rankine plant (§4 → `engines-rankine-steam-engines-and-turbines`).

### Manufacturing processes

Process choice is **driven by volume and geometry, not aesthetic preference. At 10 units, machine
everything. At 10,000, cast or forge. Tooling amortization is the entire economics.**

- **Casting.** Sand casting for blocks and large parts (cheap, rough, excellent for low-to-medium
  volume). Die casting for high-volume non-ferrous parts. Investment (lost-wax) casting for turbine
  blades (excellent detail, complex internal cooling channels).
- **Forging.** Cranks, rods, gears — anything needing superior fatigue properties. Forging aligns the
  metal's grain flow with the part's stress directions, which is why forged parts are stronger than
  cast parts of the same material.
- **Machining.** Turning, milling, drilling, boring, grinding; CNC machining centres handle most engine
  component finishing. Design constraints: internal corners carry the tool radius (they cannot be
  sharp), deep narrow pockets need long thin tools that chatter and deflect, and every re-fixturing
  (setup) costs money and adds tolerance error.
- **Welding.** MIG, TIG, spot, laser, friction stir. The **heat-affected zone is where welded
  structures fail** — parent metal properties are altered, residual stresses are locked in, and
  distortion follows. Weld inspection (dye penetrant, ultrasonic, radiographic) exists because defects
  are internal.

### Tolerances — the key concept from manufacturing

Nothing is exact. A "10 mm" hole is never 10 mm; it is 10 mm ± something, and the design must work
across the whole range. **This is the single biggest mental shift from software to physical
engineering.** In software a value is the value; in hardware every dimension is a distribution, and
the design is correct only if it works everywhere in that distribution.

- **Stack-up.** Tolerances accumulate across an assembly.
  - *Worst-case tolerancing* (sum all tolerances) is **safe but astronomically unlikely and
    expensive**.
  - *Statistical tolerancing* (root-sum-square) is **realistic but assumes independence and centred
    distributions, which real processes often violate**.
- **Cost is non-linear.** Tighter tolerance costs more, often non-linearly. **Halving a tolerance can
  multiply cost several-fold** by forcing a different process or added inspection. **Over-tolerancing
  is the most common and expensive novice error in mechanical design.**
- **The rule.** The right tolerance is the **LOOSEST one that still makes the assembly work.**
- **GD&T** (Geometric Dimensioning and Tolerancing, **ASME Y14.5**) specifies **function** rather than
  just dimensions: form (flatness, straightness), orientation (perpendicularity, angularity), location
  (true position) and runout — all relative to **explicitly declared datums**. GD&T exists because
  plus/minus dimensioning is ambiguous about what matters and creates **square** tolerance zones where
  the function wants **round** ones.

The rebuild measurements in §18 are this section applied: a 0.02–0.05 mm bearing clearance and a
0.05 mm-in-100 mm deck flatness limit are tolerance bands, and an engine assembled outside them fails
in service however carefully it was cleaned.
