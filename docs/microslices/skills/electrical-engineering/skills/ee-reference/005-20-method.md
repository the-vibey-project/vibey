---
id: skill-20-method-15f2fe0645
purpose: 20 method
source: src/vibey_tools/skills/plugins/electrical-engineering/skills/ee-reference/SKILL.md
requires: ["skill-19-quick-reference-46c6c1fcfc"]
links: []
---

## §20. Method

**No searches were run, and none were warranted.** ⚠️ **This is settled physics and mature
practice**: Ohm 1827, Kirchhoff 1845, Heaviside's transmission-line work in the 1880s,
and the CMOS/TTL threshold conventions have been fixed for decades. **Component part
numbers and prices move constantly; none of the content here depends on them.**

**Sources** are the standard references in §18 — chiefly **Horowitz & Hill** for practical
circuit design, **Johnson & Graham** for §9 → `ee-signal-integrity-emc-and-pcb-design` and §10 → `ee-signal-integrity-emc-and-pcb-design` (⚠️ **the high-speed material is
substantially their framing, including the `0.35/t_rise` knee rule and the
return-current-under-the-trace principle**), **Ott** for EMC, and vendor application notes,
which in this field are frequently better than textbooks.

**Scoped to complement**: MCU selection, buses, and firmware architecture sit in an
embedded-IoT reference; DSP in a signal-processing reference; the semiconductor
*fabrication* process in a nanotechnology reference. **This is the circuit layer they all
assume.**

**Confidence: high throughout.** The equations are standard and stated with their validity
conditions — ⚠️ **the conditions are the valuable part, since most errors here come from
applying a correct formula outside its assumptions** (an unloaded divider, a `R_DS(on)`
at the wrong `V_GS`, a `θ_JA` from a different board).

⚠️ **Three deliberate hedges.** **Numerical values in §17 are representative** — logic
thresholds vary by family and vendor, `V_f` varies with current and temperature, and
propagation delay depends on the dielectric. **Always check the specific datasheet.**
**The §9.3 → `ee-signal-integrity-emc-and-pcb-design` note that paralleling many different capacitor values is now considered dubious
reflects a genuine shift in practice** away from older advice, and ⚠️ **you will still find
the old guidance widely repeated** — the anti-resonance argument is the reason for the
change. And **§14 → `ee-test-selection-safety-and-debugging` is orientation, not a safety qualification**: ⚠️ **the current thresholds
are widely-cited approximations that vary with path, duration, frequency and individual.
If you are working on mains and unsure, get someone qualified.**
