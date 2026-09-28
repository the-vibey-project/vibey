---
id: skill-7-resistance-and-ohm-s-law-938bbb280c
purpose: 7 resistance and ohm s law
source: src/vibey_tools/skills/plugins/electromagnetism-and-electricity/skills/em-current-energy-flow-circuits-and-ac/SKILL.md
requires: ["skill-6-what-current-actually-is-f4b4c281ba"]
links: ["skill-8-where-the-energy-actually-flows-52b7b66e5c"]
---

## §7. Resistance and Ohm's Law

**⚠️ V = IR is a MATERIAL BEHAVIOUR, not a law of nature.** ⚠️ **Many things are not ohmic:
diodes, transistors, filaments (resistance rises with temperature), thermistors, arcs
(negative resistance region), and most of the interesting components.**
**⚠️ Resistivity ρ and its temperature coefficient**: ⚠️ **metals increase resistance with
temperature (more phonon scattering); semiconductors DECREASE (more carriers) — an
inversion that follows directly from §20 → `em-conduction-semiconductors-grounding-and-electrical-safety`'s band picture.**
**⚠️ R = ρL/A**, **and ⚠️ the SKIN EFFECT confines high-frequency current to a thin surface
layer, making effective A much smaller and AC resistance much higher than DC.**
> **⚠️ GOTCHA — "current takes the path of least resistance" is FALSE.** ⚠️ **Current takes
> ALL available paths, dividing in inverse proportion to resistance.** **⚠️ The correct
> version matters in practice: a fault current does not politely go down the earth
> conductor and ignore the person in parallel with it.**
> **⚠️ The higher-frequency version is even less intuitive: return current follows the
> path of least IMPEDANCE, which above a few hundred kHz means it flows directly beneath
> the signal trace to minimize loop inductance — not by the shortest route** (§24 → `em-conduction-semiconductors-grounding-and-electrical-safety`).

---
