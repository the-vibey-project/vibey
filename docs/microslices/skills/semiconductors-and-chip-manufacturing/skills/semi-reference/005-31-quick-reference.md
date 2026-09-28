---
id: skill-31-quick-reference-80f36a758c
purpose: 31 quick reference
source: src/vibey_tools/skills/plugins/semiconductors-and-chip-manufacturing/skills/semi-reference/SKILL.md
requires: ["skill-30-sources-3253ebce07"]
links: ["skill-32-method-1b790a9280"]
---

## §31. Quick Reference

### 31.1 Picker
| Question | Where |
|---|---|
| Is "3nm" better than "4nm"? | ⚠️ **Meaningless across foundries. Compare density** (§5 → `semi-carriers-doping-junctions-mosfet-and-scaling`) |
| Why did clock speeds stop rising? | ⚠️ **Dennard scaling ended; voltage couldn't follow** (§5 → `semi-carriers-doping-junctions-mosfet-and-scaling`) |
| Why so many specialized accelerators? | ⚠️ **Dark silicon — you can't power it all** (§5 → `semi-carriers-doping-junctions-mosfet-and-scaling`) |
| Why chiplets? | ⚠️ **Yield vs area, plus the reticle limit** (§17 → `semi-integration-yield-metrology-test-and-packaging`, §20 → `semi-integration-yield-metrology-test-and-packaging`) |
| Why is my big die so expensive? | ⚠️ **Exponential yield loss** (§17 → `semi-integration-yield-metrology-test-and-packaging`) |
| Why does EUV cost so much? | ⚠️ **Vacuum, reflective optics, tin plasma, one supplier** (§11 → `semi-cleanroom-lithography-deposition-etch-and-cmp`, §26 → `semi-pcb-assembly-reliability-design-flow-and-economics`) |
| Where's the AI hardware bottleneck? | ⚠️ **Packaging and HBM, not logic** (§27.2) |
| Should we design for the leading node? | ⚠️ **Mask cost sets minimum volume** (§16 → `semi-integration-yield-metrology-test-and-packaging`, §25 → `semi-pcb-assembly-reliability-design-flow-and-economics`) |
| Why does the board material matter? | ⚠️ **Loss tangent and impedance at speed** (§21 → `semi-pcb-assembly-reliability-design-flow-and-economics`) |
| Why did the solder joint crack? | ⚠️ **CTE mismatch under thermal cycling** (§23 → `semi-pcb-assembly-reliability-design-flow-and-economics`) |
| Does running hot matter? | ⚠️ **Arrhenius. It consumes rated life** (§23 → `semi-pcb-assembly-reliability-design-flow-and-economics`) |
| Why does ECC exist? | ⚠️ **Soft errors are physics, not defects** (§23 → `semi-pcb-assembly-reliability-design-flow-and-economics`) |

### 31.2 Design and sourcing checks
- [ ] ⚠️ **Node chosen on density/PPA and mask cost, not on the name** (§5 → `semi-carriers-doping-junctions-mosfet-and-scaling`, §25 → `semi-pcb-assembly-reliability-design-flow-and-economics`)
- [ ] ⚠️ **Die size checked against yield model and reticle limit** (§17 → `semi-integration-yield-metrology-test-and-packaging`)
- [ ] Chiplet partition justified against known-good-die test cost (§19 → `semi-integration-yield-metrology-test-and-packaging`, §20 → `semi-integration-yield-metrology-test-and-packaging`)
- [ ] ⚠️ **Packaging technology and CAPACITY secured, not assumed** (§20 → `semi-integration-yield-metrology-test-and-packaging`, §27.2)
- [ ] HBM or memory allocation confirmed if relevant (§27.2)
- [ ] ⚠️ **Thermal path designed for the package, not just the die** (§20 → `semi-integration-yield-metrology-test-and-packaging`, §23 → `semi-pcb-assembly-reliability-design-flow-and-economics`)
- [ ] DFT coverage adequate and test time budgeted (§19 → `semi-integration-yield-metrology-test-and-packaging`)
- [ ] ⚠️ **DFM and density rules met — dummy fill, hot spots** (§15 → `semi-cleanroom-lithography-deposition-etch-and-cmp`, §17 → `semi-integration-yield-metrology-test-and-packaging`) |
- [ ] Board stack-up: impedance, loss tangent, return paths (§21 → `semi-pcb-assembly-reliability-design-flow-and-economics`)
- [ ] ⚠️ **Reliability targets stated with temperature and voltage** (§23 → `semi-pcb-assembly-reliability-design-flow-and-economics`)
- [ ] ⚠️ **Single-source dependencies identified across the BOM** (§26 → `semi-pcb-assembly-reliability-design-flow-and-economics`)

---
