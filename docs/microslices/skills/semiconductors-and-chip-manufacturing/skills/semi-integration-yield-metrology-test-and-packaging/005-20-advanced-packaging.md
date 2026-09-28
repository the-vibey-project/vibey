---
id: skill-20-advanced-packaging-43fc30df1f
purpose: 20 advanced packaging
source: src/vibey_tools/skills/plugins/semiconductors-and-chip-manufacturing/skills/semi-integration-yield-metrology-test-and-packaging/SKILL.md
requires: ["skill-19-test-f91287a331"]
links: []
---

## §20. ⚠️ Advanced Packaging

> **⚠️ Historically an afterthought; now the most strategically important part of the
> chain** (§27.2 → `semi-reference`).
```
⚠️ WHAT PACKAGING DOES  ⚠️ electrical connection · POWER delivery ·
   ⚠️ HEAT removal · mechanical protection · and ⚠️ matching the
   chip's micron-scale pitch to the board's millimetre scale
⚠️ TRADITIONAL  wire bond · flip chip (⚠️ solder bumps, area array,
   far better electrically) · BGA
⚠️ 2.5D  ⚠️ multiple dies side by side on a SILICON INTERPOSER with
   fine wiring. ⚠️ TSMC's CoWoS is the dominant example — this is
   how a GPU sits next to HBM stacks
   ⚠️ EMIB (Intel) embeds a small silicon bridge in the substrate
   instead of a full interposer — cheaper, no through-silicon
   interposer needed
⚠️ 3D  ⚠️ dies stacked vertically, connected by THROUGH-SILICON VIAS
   ⚠️ HYBRID BONDING  ⚠️ direct copper-to-copper and oxide-to-oxide
   bonding with no solder — ⚠️ enables micron-scale pitch, far
   denser than microbumps, and it is becoming essential (§27.2)
⚠️ FAN-OUT WAFER LEVEL PACKAGING  redistribution layers, no substrate
⚠️ CHIPLETS  ⚠️ partition a design into dies, each on the process
   node that suits it — logic on the leading edge, I/O and analog
   on cheaper mature nodes. ⚠️ Yield (§17), cost and reticle limit
   all push this way
⚠️ UCIe  ⚠️ the standard die-to-die interconnect, aiming at an open
   chiplet ecosystem
⚠️ THE HARD PARTS  ⚠️ thermal (stacked dies trap heat) · warpage
   from CTE mismatch · ⚠️ known good die (§19) · ⚠️ ABF SUBSTRATE
   supply, which is concentrated and has had long lead times ·
   power delivery through the stack
```
