---
id: skill-9-circuit-theory-and-its-validity-550f5a05b9
purpose: 9 circuit theory and its validity
source: src/vibey_tools/skills/plugins/electromagnetism-and-electricity/skills/em-current-energy-flow-circuits-and-ac/SKILL.md
requires: ["skill-8-where-the-energy-actually-flows-52b7b66e5c"]
links: ["skill-10-ac-and-impedance-220fbadecd"]
---

## §9. ⚠️ Circuit Theory and Its Validity

```
⚠️ KIRCHHOFF'S CURRENT LAW = charge conservation (§6)
⚠️ KIRCHHOFF'S VOLTAGE LAW = ⚠️ conservative field — and it FAILS
   when there is a changing magnetic flux through the loop (§13),
   which is exactly why a probe loop in a switching supply reads
   voltages that "shouldn't be there"
⚠️ THE VALIDITY CONDITION  circuit dimensions ≪ wavelength.
   ⚠️ Rule of thumb: if the physical size exceeds roughly a tenth of
   a wavelength, use transmission line theory (§18)
```
**⚠️ Analysis tools**: **nodal and mesh analysis, Thévenin and Norton equivalents,
superposition (⚠️ linear circuits only), and the maximum power transfer theorem
(⚠️ which maximizes POWER, not efficiency — at matched impedance you dissipate half the
power in the source, which is why power distribution deliberately does NOT match).**
**⚠️ Time domain**: **RC and RL time constants (τ = RC, L/R), and ⚠️ RLC damping regimes.**
**⚠️ The parasitics are the real circuit at high frequency**: ⚠️ **every capacitor has
series inductance (ESL) and resistance (ESR) and therefore SELF-RESONATES, above which it
behaves as an inductor; every inductor has parallel capacitance; every wire has
inductance.** ⚠️ **A "100 nF decoupling capacitor" stops decoupling above its self-resonant
frequency, which is why multiple values in parallel are used.**

---
