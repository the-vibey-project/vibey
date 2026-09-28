---
id: skill-14-house-power-systems-f636946bf6
purpose: 14 house power systems
source: src/vibey_tools/skills/plugins/engines-generators-and-fuels/skills/engines-generators-and-house-power/SKILL.md
requires: ["skill-13-generator-types-and-ac-vs-dc-generation-f459a291ca"]
links: []
---

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

> **NEUTRAL BONDING IS CONDITIONAL — IT DEPENDS ON THE TRANSFER SWITCH.** Any one system gets its
> neutral bonded to ground at exactly **one** point. *Which* point, and whether the generator needs a
> grounding electrode of its own, depends on whether the generator is a **separately derived system**
> — and that is decided by whether the transfer switch switches the neutral.
>
> - **The transfer switch switches the neutral** (the neutral opens along with the hots): the
>   generator is separately derived. The bond belongs at the generator, and a permanently installed
>   separately derived system normally also needs its own grounding-electrode connection.
> - **The transfer switch does not switch the neutral** (generator neutral stays tied to the service
>   neutral): the generator is *not* separately derived. The single bond stays at the service
>   equipment and the generator must be **unbonded** — this is the difference between a
>   "bonded-neutral" and a "floating-neutral" machine, and many portable generators ship bonded.
>
> Get this wrong in either direction and it bites: two bonds put neutral current onto equipment
> grounding conductors and metal that is not meant to carry it, while no bond anywhere leaves fault
> current without a low-impedance return path, so protective devices may not trip. Cord-and-plug
> portable use is a separate case again.
>
> **This is not a rule you pick from a reference.** Follow the generator and transfer-switch
> manufacturer's installation instructions, and have a licensed electrician establish which case your
> installation is, to your local electrical code, and inspect the result.

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
