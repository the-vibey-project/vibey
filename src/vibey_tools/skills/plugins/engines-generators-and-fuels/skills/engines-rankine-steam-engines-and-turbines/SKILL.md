---
name: engines-rankine-steam-engines-and-turbines
description: "Use when analysing or designing a steam plant, sizing or improving a Rankine cycle, choosing between a reciprocating steam engine and a turbine, working out cut-off, compounding, superheat, reheat, regenerative feedwater heating, supercritical operation or condenser vacuum, or planning an actual steam build from a model boiler up to a 1-10 kW set. Covers the four Rankine components and processes, the five improvements that take real plants from 25-30% to 45-47%, impulse and reaction turbine theory, and the boiler safety rules that come before any of it. Part 2 of the Engines, Generators and Fuel Sources reference."
---

# The Rankine Cycle, Steam Engines and Turbines

> **Part 2 of 7** of the *Engines, Generators, and Fuel Sources* reference (plugin
> `engines-generators-and-fuels`), covering §4–§6 — the Rankine cycle and its five improvements, reciprocating engines and turbines, and what you would actually build. Sibling skills:
> `engines-thermodynamics-and-the-carnot-ceiling` (§1–§3 — the four laws, the Carnot ceiling, working fluids and phase behaviour),
> `engines-otto-diesel-brayton-stirling-and-combined-cycles` (§7–§11 — internal combustion, gas turbines, the Stirling engine, and the combined cycle),
> `engines-generators-and-house-power` (§12–§14 — Faraday to a wired house: generator theory, the four machine types, and designing or buying a house system),
> `engines-fuels-and-combustion` (§15–§17 — every fuel that can be burned, transformed or harvested, with energy densities and what engine each pairs with),
> `engines-rebuilding-engines-materials-and-tolerances` (§18–§20 — engine anatomy and the rebuild process, engine management and forced induction, and the materials and tolerance thinking that makes parts real),
> `engines-safety-and-reference` (§21–§23 — the six things that kill, the glossary, and the books that actually teach this),
>
> Section numbers are **shared across the whole set**: a reference written as §N → `skill` points
> into that sibling skill. Everything here is durable engineering and physics — the laws, cycles and
> equations do not expire; efficiency figures for current plant and practice do drift.

---

## §4 The Rankine cycle

Virtually all steam engines, from the earliest locomotives to the largest nuclear power plants, run the Rankine cycle. It is the engine that launched the industrial revolution and still the dominant method of generating electricity worldwide.

Everything below is one idea in different clothes — **move heat addition to a HIGHER average temperature, or heat rejection to a LOWER one** (the universal design principle; the Carnot ceiling it serves is §2 → `engines-thermodynamics-and-the-carnot-ceiling`).

### Four components, four processes

| # | Component | Process | What happens | Why it matters |
|---|---|---|---|---|
| 1 | **Pump** | Isentropic compression | Liquid water pressurized from condenser pressure to boiler pressure | Requires very little work — liquid water is nearly incompressible. The smallest energy consumer in the cycle. |
| 2 | **Boiler** | Constant-pressure heat addition | Heat from combustion (or nuclear fission, or concentrated solar) is added: sensible heat to saturation, latent heat to evaporate, and in modern plants superheat beyond saturation | **This is where T_H lives.** |
| 3 | **Turbine (or piston/expander)** | Isentropic expansion | High-pressure, high-temperature steam expands, producing work; pressure and temperature drop | In a condensing engine it expands to a vacuum — and that vacuum matters as much as boiler pressure, because it lowers T_C. |
| 4 | **Condenser** | Constant-pressure heat rejection | Expanded steam is condensed back to liquid at low pressure, rejecting heat to the environment (cooling tower, river, lake, or air-cooled condenser) | **This is where T_C lives.** |

The pump then sends condensed water back to the boiler. The working fluid never leaves the system (a **closed cycle**), which is why steam plants can use highly purified water and avoid scale and corrosion.

### Efficiency and the back-work advantage

    η = (W_turbine − W_pump) / Q_boiler = [(h_3 − h_4) − (h_2 − h_1)] / (h_3 − h_2)

Pump work is typically **only 1–2% of turbine work** — the **back-work ratio is very low**, unlike gas turbines where the compressor consumes 50–65% of turbine output (§9 → `engines-otto-diesel-brayton-stirling-and-combined-cycles`). Pressurizing a liquid is cheap; compressing a gas is expensive. This is the Rankine cycle's key structural advantage.

### The five improvements — how real plants reach 40–45%

Ideal Rankine with saturated steam achieves maybe **25–30%**. Real plants achieve **35–45%** via:

| # | Improvement | Mechanism | Figures |
|---|---|---|---|
| 1 | **Superheat** | Heat steam above saturation after evaporation. Raises the average temperature of heat addition and reduces turbine-exhaust moisture (wet steam erodes blades at high speed — a real engineering limit) | Modern superheaters reach **540–600°C**; ultra-supercritical **620–650°C** |
| 2 | **Reheat** | After partial expansion through the HP turbine, steam returns to the boiler for a reheater pass, then to the IP/LP turbine. Raises average heat-addition temperature and keeps exhaust moisture down | Most large plants use **one or two** reheat stages |
| 3 | **Regenerative feedwater heating** | Steam bled from the turbine at intermediate points preheats feedwater before the boiler. Less heat need be added at low temperature, raising the average temperature of heat addition | A large plant may have **6–8** feedwater heaters. **The single most impactful efficiency improvement after superheat.** |
| 4 | **Supercritical operation** | Above water's critical point (**221 bar, 374°C**) there is no distinct boiling phase; water transitions continuously from liquid-like to gas-like. Eliminates the constant-temperature evaporation step that pins part of the heat addition to a relatively low saturation temperature | Supercritical **42–45%**; ultra-supercritical (**300+ bar, 600–650°C**) **45–47%** |
| 5 | **Condensing at vacuum** | The condenser operates well below atmospheric. Condensing *creates* the vacuum, because water occupies about **1600× less volume** as liquid than vapour. Lowers T_C dramatically | Typically **30–50 mbar absolute** (saturation temperature **25–35°C**) |

> **That the vacuum matters as much as the boiler pressure is the most underappreciated principle in steam
> engineering.**

### Worked comparison — why condensing matters so much

Early steam engines exhausted to atmosphere, so T_C ≈ 100°C at 1 bar. A condensing engine exhausting to 30 mbar rejects heat at about 25°C. With a 600°C (873 K) boiler:

| Exhaust condition | T_C | Carnot ceiling |
|---|---|---|
| Atmospheric exhaust, 1 bar | 373 K (100°C) | 1 − 373/873 = **57%** |
| Condensing to 30 mbar | 298 K (25°C) | 1 − 298/873 = **66%** |

A **16% relative improvement in the ceiling alone** — with no change whatsoever to the hot end.

**James Watt's key invention was the separate condenser**, which gave the vacuum without cooling the cylinder, and it **roughly doubled steam-engine efficiency**.

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

## §6 Practical steam design

> ## ⚠ SAFETY FIRST — BOILERS KILL
>
> **Pressurized steam carries enormous energy. A small boiler at 10 bar contains enough stored energy to launch shrapnel through walls. Boiler explosions were the leading industrial killer of the 19th century. Any steam engine build requires: (1) a boiler designed to recognized code (ASME in the US, equivalent elsewhere), (2) a certified pressure relief valve, (3) a low-water cutoff, (4) proper water treatment, (5) regular inspection. For a model or small engine, work at low pressure (1–3 bar) and treat every component as if it could fail. Never cap or bypass the safety valve. Never operate a boiler unattended.**

Read this before anything below it. The full boiler-explosion and high-pressure-steam hazard treatment is §21 → `engines-safety-and-reference`.

### Small steam engine (model / educational)

| Element | Specification |
|---|---|
| **Boiler** | A vertical **fire-tube (Cornish type)** boiler is the simplest practical design — a steel or copper shell with tubes carrying hot gases from a burner through the water space. **Copper is preferred for models** (easy to silver-solder, excellent thermal conductivity). Must have a **water gauge glass, a pressure gauge, a safety valve set to lift at design pressure, and a filler plug**. **1–3 bar (15–45 psi)** is sufficient and relatively safe. |
| **Engine** | Single-cylinder **double-acting** reciprocating. Double-acting means steam acts on both sides of the piston alternately (admission one side while exhausting the other), **doubling power per cylinder** and giving more uniform torque. Cylinder brass or bronze with a honed bore; piston uses **PTFE or graphite rings** for low friction at temperature; **slide valve (D-valve)** driven by an eccentric on the crankshaft, or a **piston valve** for better efficiency; steel connecting rod and crankshaft; bronze bearings for the crank journals. |
| **Cut-off control** | A simple fixed-cut-off slide valve is adequate; a **Walschaerts-type linkage with variable cut-off** demonstrates the efficiency principle beautifully — you can watch steam consumption drop as you notch up. |
| **Condenser** (optional, educational) | Even a coil of copper tube in a bucket of water demonstrates the vacuum principle. Connect the exhaust to a sealed cooled container and the condensing steam creates a vacuum that pulls the piston on the exhaust stroke, **measurably increasing power and efficiency**. |
| **Output** | At **2–3 bar with a 20–30 mm bore, perhaps 10–50 W** — enough to spin a small generator (a small DC motor driven backwards, or a PMA) and light an LED. Demonstrates the complete chain **fuel → heat → steam → mechanical work → electricity**. |

Generator selection for that last step: §13 → `engines-generators-and-house-power`.

### Larger steam engine (1–10 kW)

**Safety becomes genuinely critical; a boiler at 10–15 bar is a bomb if it fails. Not a beginner project.**

| Element | Specification |
|---|---|
| **Boiler** | A **monotube (once-through)** boiler is safer than a fire-tube because it holds very little water at any moment — tubing contains **a few litres rather than hundreds**. Water is pumped continuously through a long coiled tube heated by a burner and emerges as steam. **If water flow stops the tube overheats rapidly, so a reliable feed pump and low-flow cutoff are essential.** Monotube boilers can produce **10–20 bar at 300–400°C**. |
| **Engine** | Single-stage or compound reciprocating, or a small single-stage impulse turbine. A well-designed reciprocating engine with **50–80 mm bore** and a condenser can achieve **15–20% thermal efficiency**. A small turbine (Tesla or single-stage impulse) is simpler mechanically but **less efficient at small scale** (tip-clearance losses and low Reynolds numbers). |
| **Generator** | A **PMA or wound-field alternator**, belt-driven or direct-coupled. A modified automotive alternator (with a proper regulator) can work for low output; a **purpose-built alternator is better**. |

### The practical efficiency chain

| Stage | Efficiency |
|---|---|
| Combustion (in a good boiler) | **80–90%** |
| Steam cycle | **15–25%** small reciprocating · **20–30%** small turbine |
| Mechanical-to-electrical | **85–95%** |
| **Overall fuel-to-electricity** | **10–20%** |

Low compared with a commercial combined-cycle plant at **60%** — but those are **500 MW machines at 250 bar and 600°C**. (The combined cycle and why it wins: §11 → `engines-otto-diesel-brayton-stirling-and-combined-cycles`.)
