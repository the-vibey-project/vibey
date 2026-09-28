---
id: skill-28-misconceptions-480f24f425
purpose: 28 misconceptions
source: src/vibey_tools/skills/plugins/semiconductors-and-chip-manufacturing/skills/semi-reference/SKILL.md
requires: ["skill-27-what-s-live-checked-august-2026-5b2be1741c"]
links: ["skill-29-numbers-0e3ac01db9"]
---

## §28. Misconceptions

| Misconception | Correction |
|---|---|
| "3nm" is a physical dimension | ⚠️ **A marketing name since ~22nm. Compare density instead** (§5 → `semi-carriers-doping-junctions-mosfet-and-scaling`) |
| Moore's Law is a law of physics | ⚠️ **An economic observation about cost per transistor** (§5 → `semi-carriers-doping-junctions-mosfet-and-scaling`) |
| Moore's Law ended | ⚠️ **Density still rises; DENNARD scaling ended, and cost/transistor stalled** (§5 → `semi-carriers-doping-junctions-mosfet-and-scaling`) |
| Multicore happened because parallel is better | ⚠️ **Frequency scaling stopped. It was forced** (§5 → `semi-carriers-doping-junctions-mosfet-and-scaling`) |
| Voltage can keep scaling down | ⚠️ **60 mV/decade subthreshold floor blocks it** (§4 → `semi-carriers-doping-junctions-mosfet-and-scaling`, §5 → `semi-carriers-doping-junctions-mosfet-and-scaling`) |
| Transistors are the speed limit | ⚠️ **Interconnect RC dominates at the leading edge** (§7 → `semi-transistor-architectures-interconnect-memory-and-wafers`) |
| SRAM shrinks with logic | ⚠️ **It has scaled poorly, which drives chiplet partitioning** (§8 → `semi-transistor-architectures-interconnect-memory-and-wafers`) |
| EUV is just a shorter wavelength | ⚠️ **Everything absorbs it — vacuum, all-reflective optics, tin plasma** (§11 → `semi-cleanroom-lithography-deposition-etch-and-cmp`) |
| Bigger chips are better | ⚠️ **Yield falls exponentially with area** (§17 → `semi-integration-yield-metrology-test-and-packaging`) |
| Chiplets are about modularity | ⚠️ **Primarily yield and the reticle limit** (§17 → `semi-integration-yield-metrology-test-and-packaging`, §20 → `semi-integration-yield-metrology-test-and-packaging`) |
| Chiplets are strictly cheaper | ⚠️ **Known-good-die testing adds 15–30% test cost** (§19 → `semi-integration-yield-metrology-test-and-packaging`) |
| Packaging is an afterthought | ⚠️ **It's the binding constraint for AI silicon** (§20 → `semi-integration-yield-metrology-test-and-packaging`, §27.2) |
| A fab's cost is the building | ⚠️ **Tools. One EUV scanner is hundreds of millions** (§25 → `semi-pcb-assembly-reliability-design-flow-and-economics`, §27.1) |
| Chips are made where they're designed | ⚠️ **Fabless/foundry split; leading edge is concentrated** (§25 → `semi-pcb-assembly-reliability-design-flow-and-economics`, §26 → `semi-pcb-assembly-reliability-design-flow-and-economics`) |
| The leading edge is most of the industry | ⚠️ **Most chips by unit come from mature nodes** (§25 → `semi-pcb-assembly-reliability-design-flow-and-economics`) |
| Copper is etched like aluminium | ⚠️ **It isn't — hence damascene and CMP** (§13 → `semi-cleanroom-lithography-deposition-etch-and-cmp`, §15 → `semi-cleanroom-lithography-deposition-etch-and-cmp`) |
| Annealing is straightforward heating | ⚠️ **Thermal budget: heat activates AND diffuses** (§14 → `semi-cleanroom-lithography-deposition-etch-and-cmp`) |
| Dummy metal fill is wasted area | ⚠️ **CMP density rules require it** (§15 → `semi-cleanroom-lithography-deposition-etch-and-cmp`) |
| A chip either works or doesn't | ⚠️ **Binning monetizes partial failures** (§17 → `semi-integration-yield-metrology-test-and-packaging`) |
| Overclocking only risks crashes | ⚠️ **It consumes rated lifetime — TDDB, electromigration** (§23 → `semi-pcb-assembly-reliability-design-flow-and-economics`) |
| Memory bit flips are defects | ⚠️ **Cosmic rays and alphas. Hence ECC** (§23 → `semi-pcb-assembly-reliability-design-flow-and-economics`) |
| FR-4 is fine for any board | ⚠️ **Its loss tangent destroys multi-GHz signals** (§21 → `semi-pcb-assembly-reliability-design-flow-and-economics`) |
| Lead-free solder was a pure improvement | ⚠️ **Higher melting, narrower window, tin whiskers** (§22 → `semi-pcb-assembly-reliability-design-flow-and-economics`) |
| High-NA EUV is obviously the next step | ⚠️ **TSMC is sitting it out on cost grounds** (§27.1) |
| AI chips are limited by logic wafers | ⚠️ **~90% of CoWoS and HBM vs ~12% of logic dies** (§27.2) |
| Announced HBM capacity means supply | ⚠️ **Capacity that fails qualification doesn't ship** (§27.2) |

---
