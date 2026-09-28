---
id: skill-21-safety-the-things-that-kill-728f5eb5d6
purpose: 21 safety the things that kill
source: src/vibey_tools/skills/plugins/engines-generators-and-fuels/skills/engines-safety-and-reference/SKILL.md
requires: []
links: ["skill-22-glossary-82df7851df"]
---

## §21 Safety — the things that kill

Six hazard families. Each one has killed people doing exactly what this reference describes.
Nothing below is advisory.

| Hazard | The mechanism | The one rule you must not break |
|---|---|---|
| Boiler explosions | Low water → overheated metal → rupture → water flashes to steam at 1600× volume | Never bypass, cap or plug a safety valve |
| Carbon monoxide | Incomplete combustion; CO binds haemoglobin more tightly than oxygen | Never run an engine or generator indoors or in a partially enclosed space |
| Electrical hazards | 100 mA across the chest causes ventricular fibrillation; batteries deliver enormous short-circuit current | Turn off and lock out, then verify de-energized with a meter |
| Fuel storage and fire | Petrol vapour (flash point −40°C) and propane are heavier than air and pool in low areas | Never store propane cylinders indoors or below grade; keep petrol in approved containers away from ignition sources and living spaces |
| High-pressure steam | Steam at 10 bar / 180°C causes instantaneous third-degree burns and is invisible at the leak | Hydrostatic-test with water before applying heat |
| Mechanical energy | Rotating shafts, belts and couplings grab; springs store energy; jacks fail | Guards are not optional; jack stands, never jacks alone |

### 21.1 Boiler explosions

**A pressurized boiler is a bomb.** If the water level drops below the firetubes (or the crown
sheet in a locomotive boiler), the metal overheats, weakens and ruptures. The sudden release of
pressurized water flashes to steam at 1600× volume, producing a blast that can level a building.

Prevention — all of it, not a selection:

- A working water gauge.
- A low-water cutoff (automatic fuel shutoff if water is low).
- A safety valve.
- Proper water treatment — scale insulates and causes local overheating.
- Regular inspection by a qualified person.
- **Never bypass, cap or plug a safety valve.**
- **Never operate a boiler you have not inspected.**

Boiler explosions were the leading industrial killer of the 19th century. The design-side rules —
build to a recognized code (ASME in the US, equivalent elsewhere), certified pressure relief valve,
low-water cutoff, water treatment, regular inspection, low pressure (1–3 bar) for models, never
operate unattended — live with the build guidance at §6 → `engines-rankine-steam-engines-and-turbines`.

### 21.2 Carbon monoxide

**CO is colourless and odourless**, produced by incomplete combustion. It kills by binding to
haemoglobin more tightly than oxygen, causing hypoxia. **It is produced by every engine and every
fire.**

- Never run an engine or generator indoors or in a partially enclosed space.
- Generators must be at least **6 metres (20 feet)** from any building opening, with exhaust
  directed away.
- CO detectors are **mandatory** in any building with a fuel-burning appliance or attached garage.
- Symptoms: headache, dizziness, nausea, confusion — progressing to unconsciousness and death.
- **If you feel them around an engine, get to fresh air immediately.**

### 21.3 Electrical hazards

**Mains voltage (120 or 230 V) can kill, and generator output is mains voltage.** Current through
the body — as little as **100 mA across the chest** — can cause ventricular fibrillation. DC from
battery banks (especially 48 V and above) can also be lethal and can deliver enormous current if
shorted: a 12 V car battery can deliver **500+ amps** through a wrench dropped across the terminals,
with arc-flash and fire consequences.

Rules:

- Turn off and lock out power before working.
- Verify de-energized with a meter.
- Use insulated tools.
- Never work on live equipment alone.
- Ground everything properly.
- Use GFCI/RCBO protection.
- Respect stored energy in capacitors and batteries.

Related and equally non-negotiable: **never backfeed through a wall outlet**. Neutral bonding and
whether a grounding electrode is required depend on the generator's listed transfer equipment,
whether it is separately derived, the manufacturer's instructions, and local electrical code — the
transfer-switching and grounding rules, and which way each of those inputs decides the bond, are at
§14 → `engines-generators-and-house-power`.

### 21.4 Fuel storage and fire

**Petrol is extremely flammable (flash point −40°C) and its vapours are heavier than air, pooling
in low areas.** Store in approved containers away from ignition sources and living spaces.

- **Diesel** is safer (flash point ~52°C) but still a fire hazard at elevated temperatures.
- **Propane** is heavier than air and pools too — **never store cylinders indoors or below grade.**
- Have appropriate fire extinguishers: CO₂ or dry chemical for fuel fires. **Never water on a
  liquid fuel fire.**
- Know how to shut off the fuel supply in an emergency.

### 21.5 High-pressure steam

**Steam at 10 bar and 180°C causes instantaneous third-degree burns.** Steam is **INVISIBLE at the
leak point** — you cannot see it until it condenses, which may be centimetres or metres away. **The
clear space around a high-pressure steam leak is a hazard zone.**

- Insulate all steam lines.
- Use steam-rated valves and fittings — ordinary plumbing is not adequate.
- Test systems by pressurizing with water (hydrostatic test) **before** applying heat. A water leak
  is inconvenient; a steam leak is dangerous.

### 21.6 Mechanical energy

**A rotating shaft, belt or coupling can grab clothing, hair or fingers with terrifying speed.
Guards are not optional. Never reach into a running engine.**

- Springs (valve springs, clutch pressure plate springs) store significant energy; a compressed
  spring released unexpectedly can cause serious injury — **use proper spring compressors.**
- **Jack stands, never jacks alone**, when working under a vehicle: a hydraulic jack can fail or
  roll. Jack stands on solid, level ground.
