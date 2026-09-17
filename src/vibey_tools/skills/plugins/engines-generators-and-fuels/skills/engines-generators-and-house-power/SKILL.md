---
name: engines-generators-and-house-power
description: "Use when sizing, buying, building or wiring a generator or whole-house/off-grid power system — doing a load audit with motor starting surges, matching engine RPM to a 2-pole or 4-pole generator head, choosing a store-bought genset vs built-from-components vs inverter generator, picking diesel vs petrol vs propane, sizing a battery/hybrid bank, or arranging transfer switching, grounding and neutral bonding. Also covers the underlying machine theory: Faraday's law, the EMF equation and the RPM-to-Hz rule, back-EMF and speed droop, the loss mechanisms, and the four generator types. Part 4 of the Engines, Generators and Fuel Sources reference."
---

# Electric Generators and House Power Systems

> **Part 4 of 7** of the *Engines, Generators, and Fuel Sources* reference (plugin
> `engines-generators-and-fuels`), covering §12–§14 — Faraday to a wired house: generator theory, the four machine types, and designing or buying a house system. Sibling skills:
> `engines-thermodynamics-and-the-carnot-ceiling` (§1–§3 — the four laws, the Carnot ceiling, working fluids and phase behaviour),
> `engines-rankine-steam-engines-and-turbines` (§4–§6 — the Rankine cycle and its five improvements, reciprocating engines and turbines, and what you would actually build),
> `engines-otto-diesel-brayton-stirling-and-combined-cycles` (§7–§11 — internal combustion, gas turbines, the Stirling engine, and the combined cycle),
> `engines-fuels-and-combustion` (§15–§17 — every fuel that can be burned, transformed or harvested, with energy densities and what engine each pairs with),
> `engines-rebuilding-engines-materials-and-tolerances` (§18–§20 — engine anatomy and the rebuild process, engine management and forced induction, and the materials and tolerance thinking that makes parts real),
> `engines-safety-and-reference` (§21–§23 — the six things that kill, the glossary, and the books that actually teach this),
>
> Section numbers are **shared across the whole set**: a reference written as §N → `skill` points
> into that sibling skill. Everything here is durable engineering and physics — the laws, cycles and
> equations do not expire; efficiency figures for current plant and practice do drift.

Every engine produces mechanical work — usually rotation at a shaft. To make electricity you need a
generator: the physical implementation of Faraday's law of induction.

## §12 Generator theory

### Faraday's law and the minus sign

    EMF = −dΦ/dt

A changing magnetic flux Φ through a loop induces a voltage. The minus sign (Lenz's law) means the induced current **opposes** the change — conservation of energy in disguise. If it reinforced instead, you would have a runaway energy source.

**Three ways to change the flux:** change field strength, change loop area, or change loop orientation relative to the field. All three are used in real machines; **the most common is changing orientation** — rotating a coil in a magnetic field.

### The EMF equation and the RPM → Hz consequence

    EMF = N · B · A · ω · sin(ωt)

N = turns, B = field strength, A = coil area, ω = angular velocity. Output is sinusoidal AC. Frequency f = ω/(2π), so a 2-pole machine at **3,600 RPM produces 60 Hz**; at **3,000 RPM, 50 Hz**. This single relationship is why the whole of §14 keeps returning to shaft speed.

### Back-EMF and why speed droops under load

A motor's back-EMF opposes its supply voltage:

    current drawn = (V_supply − back-EMF) / winding_resistance

For a generator, the induced EMF drives current through the load; that current produces counter-torque. Applying a load therefore slows the prime mover unless the governor (or electronic inverter) increases input power to maintain frequency. (Governor and droop: §22 → `engines-safety-and-reference`.)

### The four real loss mechanisms

Four categories; core loss splits into two sub-mechanisms.

| Loss | What it is |
|---|---|
| Copper losses | I²R in the windings |
| Core loss — hysteresis | Energy lost per magnetization cycle, proportional to the area of the B-H loop |
| Core loss — eddy currents | Circulating currents induced in the core iron, **suppressed by laminating the core** |
| Friction and windage | Mechanical drag on the rotating assembly |
| Excitation losses | Power consumed producing the magnetic field in wound-field machines |

Generator efficiency is typically **90–98% above a few kW**.

## §13 Generator types, and AC vs DC generation

| Type | How the field is produced | Typical use | Notes |
|---|---|---|---|
| Permanent Magnet (PMA) | Permanent magnets on rotor | Small wind, hydro, modified automotive alternators, portable generators | Simple, efficient, no excitation power. Voltage varies with speed — needs rectification and/or regulation. |
| Wound-Field Synchronous | DC through rotor windings via slip rings or brushless exciter | Power plants, large standby generators | Constant voltage at constant speed; field current controls output voltage; island mode or grid-parallel. |
| Induction (asynchronous) | Field induced in rotor by stator field | Wind turbines, micro-hydro | Simple, rugged, no slip rings. Needs grid or capacitor excitation for reactive power. Cannot black-start on its own. |
| Automotive alternator | Wound rotor with slip rings, field regulated by voltage regulator | Car electrical systems | Produces DC via built-in rectifier. Cheap and available. Low efficiency (50–65%) at part load. Can be modified for higher output or used for small wind/hydro. |

### AC vs DC generation

Most generators inherently produce AC. Grid-connected or whole-house generation needs AC at the correct voltage and frequency (120/240 V 60 Hz, or 230 V 50 Hz). Battery charging or direct DC loads need rectification.

PMAs produce variable-frequency AC tracking engine speed. To get stable 60 Hz you have exactly two options: **run the engine at fixed speed** (wasteful at part load), or **use an inverter** to convert variable-frequency AC → DC → clean 60 Hz AC.

**Why inverter generators win at part load:** inverter generators (e.g. Honda EU series) do exactly the second, and achieve much better part-load efficiency: engine speed varies with load, so at low load it slows, saving fuel and reducing noise. Architecture detail in §14, Option 3.

## §14 House power systems

### System architecture (complete house system)

Energy source (engine + fuel, or renewable) → generator → power conditioning (regulation, rectification, inversion) → energy storage (batteries for off-grid or backup) → distribution (panel, breakers, wiring) → control (monitoring, load management, transfer switching). **Each component must be matched to the others.**

### SAFETY — NEVER BACKFEED THROUGH A WALL OUTLET

> **NEVER BACKFEED THROUGH A WALL OUTLET.** Connecting a generator by plugging it into a wall outlet
> (backfeeding) is extremely dangerous and illegal. It energizes utility lines from your house and
> can kill a utility worker who thinks the line is dead. A proper transfer switch — manual or
> automatic — isolates the generator from the utility grid. **Non-negotiable.**
>
> A transfer switch selects between utility and generator power and makes it physically impossible to
> connect both simultaneously. An automatic transfer switch (ATS) monitors utility power, starts the
> generator when it fails, switches the load, and reverses when utility returns.

> **SINGLE-POINT NEUTRAL BONDING.** Grounding is critical: the generator frame must be grounded to an
> earth electrode, and **neutral must be bonded to ground at ONE point** — either at the generator or
> at the main panel, **never both** — parallel neutral paths and circulating currents.

Generator output is mains voltage and mains voltage kills; every generator also makes carbon monoxide. Read §21 → `engines-safety-and-reference` before running anything.

### The three options

| | Option 1: store-bought genset | Option 2: built from components | Option 3: inverter generator |
|---|---|---|---|
| What it is | Engine directly coupled to a generator, with fuel system, cooling system and control panel | Engine, generator head, coupling, control system, fuel system, cooling system, enclosure | Engine drives a PMA at variable speed; AC rectified to DC; inverter produces clean 60 Hz AC |
| Who it is for | **Correct for 99% of homeowners** | Anyone matching engine, head and drive themselves | Variable load; all premium portable generators |
| Why | The engineering is done for you, including safety interlocks, grounding, transfer switching and emissions compliance | You choose each component, at the cost of owning the speed-matching problem below | **The most efficient architecture for variable load** |

**Option 1 — store-bought genset.**
- *Sizing:* a typical home needs **5–20 kW** for whole-house backup. Do an energy audit (sum the wattages of loads you want to run simultaneously, including motor starting surges which can be **3–6× running wattage**). Over-sizing is wasteful (engines are less efficient at low load); under-sizing causes voltage drops that damage electronics and motors.
- *Fuel choice:* petrol (convenient, limited shelf life, dangerous to store in quantity); diesel (excellent for frequent/long run times, longer shelf life, more efficient, no spark ignition to fail); propane/natural gas (infinite shelf life for propane, clean-burning, can connect to utility gas for automatic operation, lower energy density); or dual-/tri-fuel for flexibility. Energy densities: §15 → `engines-fuels-and-combustion`.

**Option 2 — building from components.** Engine (small diesel or petrol, **5–20 HP**), generator head (PMA or wound-field alternator sized to the engine), coupling (direct shaft, belt, or chain with the right speed ratio), control system (voltage regulator, frequency meter, load management), fuel system, cooling system, enclosure.

*The critical matching is engine speed to generator speed.*

| Generator poles | Shaft speed for 60 Hz | Coupling |
|---|---|---|
| 2-pole | 3,600 RPM | Direct coupling works — most small engines run at 3,600 RPM |
| 4-pole | 1,800 RPM | Needs a 2:1 reduction (belt or gearbox) |

Belt drives absorb **2–5%** and need tensioning, but allow component flexibility and absorb shock loads.

*Power balance — worked through:* **1 HP ≈ 746 W**. A 10 HP engine can theoretically produce **7.46 kW**, but after generator efficiency (~90%) and drive losses (~5%) expect about **6.3 kW**. Size the engine with margin — **80% load is efficient and durable; 100% shortens engine life dramatically**.

**Option 3 — inverter generator.** Engine speed varies with load — at low load it slows, saving fuel and reducing noise. The architecture of all premium portable generators and the principle behind variable-speed standby units. The inverter also produces cleaner power (low THD), which matters for sensitive electronics.

### Sizing: the load audit

Start with a load audit: every appliance, its running wattage, and its **starting wattage** (critical for motors — well pumps, air conditioners, refrigerators need **3–6× running wattage for a few seconds**). **Size for the largest simultaneous load, not the sum of everything.**

| Scope | Typical size |
|---|---|
| Essential loads | 7–15 kW |
| Whole house including air conditioning | 15–25 kW |

### Engine selection for a house generator

| Fuel | Where it belongs, and why |
|---|---|
| **Diesel** | **Best for frequent or long-duration running** — more fuel-efficient, more durable, and diesel stores better than petrol. A small single-cylinder diesel (Lister-type or Chinese diesel) at **5–10 HP** runs for **thousands of hours** with basic maintenance, at **0.5–1.5 L/hr at rated load**. |
| **Petrol** | Cheaper, lighter and more available, but less durable at sustained high load and degrades in storage — **suitable for occasional backup**. |
| **Natural gas / propane** | Clean-burning; the fuel stores indefinitely (propane) or never needs storage (piped natural gas). Conversions of petrol engines to propane/natural gas are straightforward and common. |

Cycle background for these engines: §7–§8 → `engines-otto-diesel-brayton-stirling-and-combined-cycles`.

### Generator head selection

For 60 Hz, **2-pole needs 3,600 RPM, 4-pole needs 1,800 RPM**. Match the generator to engine speed; with a belt drive the pulley ratio sets the relationship. The generator must be rated for the engine's output with margin:

| Pairing | Result |
|---|---|
| 10 kW generator on a 10 kW engine | Fine |
| 10 kW generator on a 5 kW engine | Will only produce 5 kW |
| 5 kW generator on a 10 kW engine | A bottleneck — and the engine needs a governor to avoid overspeeding if the generator cannot absorb the power |

For an inverter system, **the inverter must be sized for peak load including motor starting surges, not just running load**.

### Battery storage and hybrid systems

A generator running 24/7 at low load is wasteful and noisy. A hybrid system runs the generator at high load for a few hours to charge a battery bank, then batteries power an inverter for the rest of the day: more efficient (the engine runs at its best BSFC point — see §22 → `engines-safety-and-reference`), quieter, and longer engine life. Size the bank for the energy needed between generator runs.

- **Lead-acid** (flooded, AGM, gel) — traditional.
- **Lithium iron phosphate (LiFePO₄)** — the modern choice: higher cycle life, higher depth of discharge, no maintenance, falling prices.

### Fuel supply and storage

| Fuel | Storage practice |
|---|---|
| Diesel | Store in steel or HDPE containers, add biocide and stabilizer for long-term storage, keep water out (condensation is the enemy — **keep tanks full to minimize airspace**) |
| Propane | Stores **indefinitely** in pressurized tanks with no degradation — an advantage for standby systems that sit unused for months |
| Natural gas | No storage needed if piped, but depends on utility reliability |
| Petrol | Use within **3–6 months**, add stabilizer, store in approved containers **away from living spaces** |

Fuel fire and vapour hazards — petrol's −40°C flash point, propane pooling below grade — are in §21 → `engines-safety-and-reference`.
