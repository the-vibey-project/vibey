---
id: skill-9-signal-integrity-and-grounding-466f144f2e
purpose: 9 signal integrity and grounding
source: src/vibey_tools/skills/plugins/electrical-engineering/skills/ee-signal-integrity-emc-and-pcb-design/SKILL.md
requires: []
links: ["skill-10-emc-and-emi-78a5c114b2"]
---

## §9. Signal Integrity and Grounding

### 9.1 ⚠️ The return current principle
**Current flows in loops.** At DC, return current takes the path of least *resistance*.
**⚠️ At high frequency, it takes the path of least *inductance* — which is directly under
the trace.**

> **⚠️ GOTCHA — this is the single most important idea in PCB design, and it explains
> most EMI and crosstalk.** **A slot or split in the ground plane under a fast trace
> forces the return current to detour around it**, creating a large loop. **That loop is
> an antenna.** It radiates, it picks up noise, and it adds inductance that ruins your
> signal. **Never route a fast signal across a plane split.**

### 9.2 Transmission lines
**⚠️ A trace behaves as a transmission line when the signal's rise time is comparable to
its propagation delay.** Rule of thumb: **treat it as a transmission line if trace length
> `t_rise × v/6`** — practically, **above roughly 1–2 inches for nanosecond edges.**

**Propagation** ≈ **6 in/ns in FR4** (≈ 150 ps/inch). **Characteristic impedance `Z₀`**
set by geometry and dielectric — typically **50 Ω single-ended, 90–100 Ω differential.**
**Reflection coefficient `Γ = (Z_L − Z₀)/(Z_L + Z₀)`** — ⚠️ **impedance mismatch reflects
energy, producing ringing, overshoot, and false clocking.**
**Termination**: series (at the source, ⚠️ **the cheapest and most common fix for point-to-
point**), parallel, Thévenin, AC.

### 9.3 Decoupling — done properly
**⚠️ The purpose is to supply transient current locally, because the supply is too far away
(inductively) to respond in nanoseconds.**
- **100 nF ceramic per power pin, as close as physically possible** —
  ⚠️ **the loop area from cap to pin to ground is what matters, not the schematic.**
- **Bulk capacitance** (10–100 µF) per board region.
- **⚠️ Via inductance dominates** — use short traces and multiple vias to the plane.
- ⚠️ **The old advice to parallel many different values is now considered dubious**: it
  can create anti-resonances between the caps. **Modern practice favours several
  same-value caps with low ESL, plus bulk.**

### 9.4 Grounding
**⚠️ "Ground" is not an equipotential — it's a conductor with impedance**, and current
flowing through it creates voltage differences. **This is ground bounce, and it is a real
signal.**
- **Single-point (star) ground** for low-frequency and analogue.
- **⚠️ Solid ground plane for anything fast** — it is the lowest-inductance return path
  available and it is worth a board layer.
- **⚠️ Analogue/digital ground splits are more often harmful than helpful** at this point.
  **A single solid plane with careful *placement* and partitioning usually beats a split**
  — because a split forces the §9.1 detour. **If you split, join at exactly one point and
  never route across the gap.**
- **Kelvin (4-wire) sensing** for current shunts and precision — ⚠️ **measure at the
  element, not through the current-carrying path.**

---
