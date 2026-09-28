---
id: skill-13-generator-types-and-ac-vs-dc-generation-f459a291ca
purpose: 13 generator types and ac vs dc generation
source: src/vibey_tools/skills/plugins/engines-generators-and-fuels/skills/engines-generators-and-house-power/SKILL.md
requires: ["skill-12-generator-theory-fa328f21c3"]
links: ["skill-14-house-power-systems-f636946bf6"]
---

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
