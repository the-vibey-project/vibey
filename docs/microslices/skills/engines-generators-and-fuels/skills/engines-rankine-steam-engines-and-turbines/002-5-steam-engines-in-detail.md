---
id: skill-5-steam-engines-in-detail-5df95aaa2e
purpose: 5 steam engines in detail
source: src/vibey_tools/skills/plugins/engines-generators-and-fuels/skills/engines-rankine-steam-engines-and-turbines/SKILL.md
requires: ["skill-4-the-rankine-cycle-09e4fc9c1c"]
links: ["skill-6-practical-steam-design-dd2ecac840"]
---

## §5 Steam engines in detail

### Reciprocating steam engines (piston)

Steam enters a cylinder, pushes a piston, linear motion becomes rotation via a crankshaft. The valvetrain (originally slide valves, later poppet valves) controls admission and exhaust timing.

**Cut-off and expansive working — the single most important efficiency concept.** Instead of admitting steam for the full stroke, the admission valve closes partway through (the "cut-off"). Steam already in the cylinder then expands adiabatically, doing work as pressure drops. **Early cut-off (20–30% of stroke)** uses steam expansively and is far more efficient per pound of steam, but produces less power per stroke.

> This is the steam engine's equivalent of a gearbox: **late cut-off (full admission) for starting and heavy load, early cut-off for cruising efficiency.** Walschaerts valve gear on locomotives varied cut-off while running.

**Compounding.** Expand steam in stages across multiple cylinders of increasing volume. A triple-expansion engine uses HP, IP and LP cylinders. Reduces temperature and pressure range per cylinder, reducing condensation losses (steam condensing on cold cylinder walls) and thermal stress. Marine steam engines were typically triple or quadruple expansion.

**Uniflow design.** Steam enters at the cylinder ends and exhausts through ports in the middle, so it always flows one way. Keeps the ends hot (admission temperature) and the middle cooler (exhaust), reducing the condensation/re-evaporation losses that plague counterflow engines where the same port handles hot admission and cold exhaust.

**Achieved efficiency — and why it is capped.**

| Configuration | Thermal efficiency |
|---|---|
| Single expansion, non-condensing → compound condensing | **5–15%** |
| Best ever: highly developed marine triple-expansion with vacuum condensers | **20–25%** |

The limit is the relatively low steam temperature and pressure possible with reciprocating mechanisms: **cylinder lubrication and piston rings limit temperature to about 300–350°C and pressure to about 15–20 bar** for practical designs.

### Steam turbines

Replaced reciprocating engines for almost all large-scale power generation: handles high temperatures and pressures far better, has no reciprocating mass (high speed with perfect balance), and scales to enormous output.

| Type | Where expansion happens | Behaviour |
|---|---|---|
| **Impulse (Rateau/Curtis stages)** | Entirely in stationary nozzles, converting pressure energy to kinetic energy (high-velocity jets) | Jets strike rotating blades (buckets); momentum transfer produces torque. Pressure drop occurs **only in the nozzles**; blades operate at constant pressure. Velocity-compounded **Curtis** stages use multiple rows of moving and stationary blades to absorb high velocity in stages. |
| **Reaction (Parsons)** | Partially in stationary blades, partially in the rotating blades | Pressure drop is **split** between stator and rotor; rotor blades see a pressure differential and a reaction force in addition to nozzle impulse. |

**Most modern turbines combine both:** impulse stages at the HP end (large pressure drops per stage), reaction stages downstream.

**The Euler turbomachine equation — the fundamental equation governing all turbomachinery.** It relates torque to the change in angular momentum of fluid passing through the rotor. Power = torque × angular velocity; work per unit mass depends on the change in the **tangential (swirl) velocity component** across the rotor. It is the angular-momentum form of the control-volume equation applied to a rotating machine.

**Specific speed.** A dimensionless group telling you which turbomachine type a duty calls for: radial
(centrifugal), mixed, or axial.

- High specific speed → **axial** (high flow, low head)
- Low specific speed → **radial** (low flow, high head)
- Steam turbines are **axial**, because they handle large flow rates at moderate head per stage.

**Blade tip speed and materials.** Maximum blade stress scales with **tip speed squared**, and tip speed is limited by material strength at temperature. LP last-stage blades are enormous (**1+ m** in large plants) because they handle huge volumes of low-pressure steam, and operate near material limits; **titanium** is sometimes used to reduce centrifugal stress through lower density. (Superalloy and materials thinking: §20 → `engines-rebuilding-engines-materials-and-tolerances`.)

### Why turbines replaced reciprocating engines

- No reciprocating mass, so **3,000–3,600 RPM (50/60 Hz)** smoothly with perfect balance.
- Handles **600°C steam at 250 bar** without lubrication problems — no piston rings sliding in a cylinder.
- Scales to **1,500 MW in a single machine**.
- A reciprocating engine at those conditions would need impossibly tough materials and would shake itself
  apart.
- The turbine's **continuous flow matches a boiler's continuous combustion**, while a reciprocating engine
  is inherently batch.

---
