---
id: skill-3-top-down-fabrication-134e2643bb
purpose: 3 top down fabrication
source: src/vibey_tools/skills/plugins/nanotechnology/skills/nano-fabrication-and-semiconductor-process/SKILL.md
requires: []
links: ["skill-4-bottom-up-synthesis-and-self-assembly-42e4a1d919"]
---

## §3. Top-Down Fabrication

**Lithography — the workhorse, and resolution is diffraction-limited:**
```
CD = k₁·λ/NA          Rayleigh criterion
DOF = k₂·λ/NA²        ⚠️ depth of focus — and note it degrades as NA²
```
**⚠️ The whole history of the industry is in that equation**: reduce λ (436 → 365 → 248 →
193 nm → **13.5 nm EUV**), raise NA (immersion in water raised it to 1.35), or reduce k₁
via resolution enhancement — **OPC, phase-shift masks, multiple patterning, and
computational lithography** (⚠️ **which is a heavy simulation workload, and where software
people actually work in this industry**).

**⚠️ Depth of focus is the underrated cost.** Higher NA buys resolution and loses DOF as
`NA²`, which is why wafer flatness and thin resists become critical problems, and why
High-NA EUV requires re-engineering the whole stack rather than swapping a lens.

**Other patterning**: **electron-beam** (⚠️ **sub-10 nm, direct-write, and hopelessly slow
— it makes the masks, not the wafers**), **focused ion beam** (mill and deposit,
⚠️ **implants gallium and damages the sample**), **nanoimprint** (mechanical stamping —
cheap, high resolution, defect-prone), **scanning probe lithography** (⚠️ **atomically
precise and glacially slow**).

**Deposition**: **PVD** (evaporation, sputtering — line-of-sight), **CVD** (conformal),
**⚠️ ALD — atomic layer deposition**, which is the enabling one: **self-limiting surface
reactions deposit one monolayer per cycle, giving Ångström thickness control and perfect
conformality into high-aspect-ratio features.** ⚠️ **No other method can wrap material
around a stacked nanosheet** (§5.2). **Epitaxy** (MBE, MOCVD) for crystalline layers.

**Etching**: **wet** (isotropic, chemically selective) vs **dry/plasma**
(⚠️ **anisotropic — RIE gives vertical sidewalls, which is what makes high-aspect-ratio
structures possible**). **Deep RIE / Bosch process** alternates etch and passivation for
very deep vertical features. **Selectivity and aspect-ratio-dependent etching** are the
practical constraints.

---
