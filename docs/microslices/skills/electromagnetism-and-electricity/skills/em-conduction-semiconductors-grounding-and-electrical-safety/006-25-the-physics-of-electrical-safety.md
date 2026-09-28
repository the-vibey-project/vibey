---
id: skill-25-the-physics-of-electrical-safety-bb63a53614
purpose: 25 the physics of electrical safety
source: src/vibey_tools/skills/plugins/electromagnetism-and-electricity/skills/em-conduction-semiconductors-grounding-and-electrical-safety/SKILL.md
requires: ["skill-24-grounding-shielding-and-emc-35fcd46460"]
links: []
---

## §25. ⚠️ The Physics of Electrical Safety

> **⚠️ CURRENT through the body causes harm, not voltage — but voltage is what drives it
> through a body of given impedance, so both matter.**
```
⚠️ APPROXIMATE EFFECTS of AC current through the body (mA, hand to hand)
   ~1        perception threshold
   ~5        painful
   ⚠️ ~10-20 "LET-GO" threshold exceeded — ⚠️ muscles contract and
             the person CANNOT RELEASE the conductor. ⚠️ This is why
             low-current shocks kill: the victim can't let go
   ⚠️ ~100+  VENTRICULAR FIBRILLATION — the usual mechanism of death
   Higher    burns, cardiac arrest, respiratory arrest
⚠️ BODY IMPEDANCE  varies hugely: ⚠️ DRY skin is a substantial
   resistance; ⚠️ WET or broken skin drops it dramatically.
   ⚠️ This is why bathrooms and outdoor sockets are high-risk
⚠️ PATH MATTERS  ⚠️ hand-to-hand or hand-to-foot crosses the heart.
   Hence the "one hand in the pocket" habit
⚠️ FREQUENCY  ⚠️ mains frequency (50/60 Hz) is close to the WORST case
   for fibrillation; higher frequencies are less dangerous
   electrically and more dangerous thermally
```
**⚠️ Protective devices and what each actually does**: ⚠️ **FUSES and BREAKERS protect the
WIRING from overcurrent — they do NOT protect people, because the fault current through a
person is far below their trip rating.** ⚠️ **RCD / GFCI devices protect PEOPLE by detecting
an imbalance between live and neutral (current going somewhere it shouldn't) and tripping
at a few tens of milliamps in milliseconds.** **⚠️ AFCIs detect arcing.**
**⚠️ Earthing** provides a low-impedance fault path so protective devices operate; ⚠️ **and
equipotential bonding prevents dangerous potential DIFFERENCES rather than eliminating
voltage.**
**⚠️ Capacitors and stored energy**: ⚠️ **large capacitors hold lethal charge long after
disconnection — CRT and switch-mode supplies especially.** **Discharge and verify.**
**⚠️ Static discharge** is high voltage, tiny energy — ⚠️ **harmless to people, routinely
destructive to semiconductors, which is why ESD precautions exist.**
