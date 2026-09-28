---
id: skill-24-grounding-shielding-and-emc-35fcd46460
purpose: 24 grounding shielding and emc
source: src/vibey_tools/skills/plugins/electromagnetism-and-electricity/skills/em-conduction-semiconductors-grounding-and-electrical-safety/SKILL.md
requires: ["skill-23-plasma-ea19d4b836"]
links: ["skill-25-the-physics-of-electrical-safety-bb63a53614"]
---

## §24. Grounding, Shielding and EMC

> **⚠️ "Ground" is the most abused word in electronics.** ⚠️ **It means at least three
> different things — earth safety connection, a circuit reference node, and a return
> current path — and conflating them causes most grounding problems.**
```
⚠️ THE CENTRAL INSIGHT (from §8)  ⚠️ CURRENT FLOWS IN LOOPS, and the
   LOOP AREA determines both radiated emission and susceptibility.
   ⚠️ Minimize loop area and most EMC problems shrink
⚠️ RETURN CURRENT PATH  ⚠️ above a few hundred kHz, return current
   flows DIRECTLY UNDER the signal trace, because that minimizes
   inductance (§7). ⚠️ Splitting a ground plane under a trace forces
   a detour and creates a large loop — a classic self-inflicted failure
⚠️ GROUND LOOPS  two "ground" points at different potentials, joined,
   giving circulating current. ⚠️ The cause of hum in audio
⚠️ SHIELDING  ⚠️ works by reflection and absorption; ⚠️ APERTURES
   matter relative to wavelength — a shield with a slot longer than
   ~λ/20 leaks badly, which is why seams and cable entries dominate
⚠️ DECOUPLING  local charge reservoirs, ⚠️ effective only below their
   self-resonant frequency (§9)
COMMON MODE vs DIFFERENTIAL MODE — ⚠️ different problems, different cures
```

---
