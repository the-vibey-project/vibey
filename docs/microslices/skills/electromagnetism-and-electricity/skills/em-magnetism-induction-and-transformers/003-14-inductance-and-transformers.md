---
id: skill-14-inductance-and-transformers-7af67a689d
purpose: 14 inductance and transformers
source: src/vibey_tools/skills/plugins/electromagnetism-and-electricity/skills/em-magnetism-induction-and-transformers/SKILL.md
requires: ["skill-13-induction-d8e977bf9e"]
links: ["skill-15-magnetic-materials-3589c0f410"]
---

## §14. Inductance and Transformers

**⚠️ Self-inductance L = Φ/I; V = L(dI/dt)** — ⚠️ **inductance resists CHANGE in current,
and its energy U = ½LI² lives in the field.**
> **⚠️ GOTCHA — interrupting current in an inductor produces a large voltage spike, because
> dI/dt is huge.** ⚠️ **This destroys switches and semiconductors, and it's why flyback
> diodes exist across relay coils and motor windings.** **⚠️ It is also the operating
> principle of ignition coils and boost converters — the same physics, deliberately
> exploited.**

**⚠️ Mutual inductance and transformers**: **V₂/V₁ = N₂/N₁, I₂/I₁ = N₁/N₂**; ⚠️ **impedance
transforms as the SQUARE of the turns ratio, which is what makes matching networks work.**
**⚠️ Transformers require CHANGING flux, so they do not work on DC** — **and applying DC
to a transformer saturates the core and burns it.**
**⚠️ Real transformer losses**: ⚠️ **copper (I²R), core hysteresis, eddy currents (§13),
leakage inductance, and winding capacitance.** ⚠️ **The reason high-voltage transmission
exists is entirely §11 → `em-current-energy-flow-circuits-and-ac`: at fixed power, higher V means lower I means I²R losses fall as
the square.**

---
