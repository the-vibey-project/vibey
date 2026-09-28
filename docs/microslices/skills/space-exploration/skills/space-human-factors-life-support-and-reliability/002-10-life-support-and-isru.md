---
id: skill-10-life-support-and-isru-31aaac84dd
purpose: 10 life support and isru
source: src/vibey_tools/skills/plugins/space-exploration/skills/space-human-factors-life-support-and-reliability/SKILL.md
requires: ["skill-9-human-physiology-the-hard-limits-953745206e"]
links: ["skill-11-radiation-environments-and-shielding-36c93afb91"]
---

## §10. Life Support and ISRU

### 10.1 ECLSS

**[DURABLE] The functions**: atmosphere pressure and composition, CO₂ removal, O₂
generation, water recovery, waste management, humidity, fire detection, and trace
contaminant control.

**How the ISS actually does it:**
- **O₂ generation**: water electrolysis (OGA).
- **CO₂ removal**: molecular sieve (CDRA).
- **⚠️ Sabatier**: `CO₂ + 4H₂ → CH₄ + 2H₂O` — recovers water from the CO₂ and the
  electrolysis hydrogen. **But it recovers only ~50% of the oxygen loop**, because the
  methane is vented. **Bosch (`CO₂ + 2H₂ → C + 2H₂O`) closes the loop fully in principle**
  and has not been operationalized — ⚠️ **carbon fouling of the catalyst is the reason.**
- **Water recovery**: urine processor plus water processor, achieving **up to ~93%
  recovery** from urine, sweat and condensate.

**⚠️ The gap between 93% and 98% is where the engineering difficulty lives**, and it
matters enormously: at 5 kg/person/day of consumables, a **1,000-day Mars mission for four
people needs 20 tonnes open-loop.** **Closure ratio is the single biggest lever on crewed
mission mass** (§1.3 → `space-mission-architecture-and-trajectory`).

**Bioregenerative systems** (MELiSSA, plant growth) close carbon and produce food,
⚠️ **at the cost of volume, power, water, and a control problem that has never been solved
at flight scale.** **Biosphere 2's failures are the standing caution.**

### 10.2 ⚠️ ISRU — and MOXIE proved the principle

**MOXIE on Perseverance was the first demonstration of ISRU on another planet.**

**The numbers**: a **15 kg, 24×24×31 cm, ~300 W** instrument performing **solid-oxide
electrolysis of atmospheric CO₂** (Mars atmosphere is ~95% CO₂) at **800 °C**. It ran
**16 times between April 2021 and August 2023**, and **at its most efficient produced
12 g of oxygen per hour at ≥98% purity — twice the original goal.**

**⚠️ Read the operational profile, because it's the honest picture**: each cycle required
**over two hours of warm-up for about one hour of production**, consuming the nominal
**~650 W·h daily payload allocation.** **Production capacity varies by up to a factor of
two** across the year and the day-night cycle with atmospheric density.

**⚠️ The energy cost is the real constraint on scaling**: MOXIE-class solid-oxide systems
need **300–700 W for ~10 g O₂/hour — about 30–70 kWh per kilogram of oxygen**, with future
scaled reactors expected to improve that by a factor of 2–3. **A Mars ascent vehicle needs
tens of tonnes of oxygen.** At even 15 kWh/kg, 30 tonnes is ~450 MWh — **which is a power
plant, not an instrument**, and is why surface fission keeps appearing in Mars
architectures (§3 → `space-power-thermal-comms-and-navigation`).

**Lunar ISRU** is a different chemistry: **molten regolith electrolysis at 3–5 kW per kg
O₂**, **hydrogen reduction at 2–3 kW/kg**, **carbothermal at 3–4 kW/kg**. **Water ice in
permanently shadowed craters** (§4 → `space-power-thermal-comms-and-navigation`) is the prize — ⚠️ **extraction is estimated at
0.2–1.0 kWh per litre of meltwater depending on depth and soil properties**, and the
resource's form and concentration remain uncertain.

**[DURABLE] Why ISRU matters at all**: the rocket equation (rocket-science §1 → `space-mission-architecture-and-trajectory`) means
propellant for the return trip, launched from Earth, costs *enormously* more than its own
mass at departure. **Making it at the destination breaks the exponential.**

---
