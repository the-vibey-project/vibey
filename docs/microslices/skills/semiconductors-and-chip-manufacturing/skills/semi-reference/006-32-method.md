---
id: skill-32-method-1b790a9280
purpose: 32 method
source: src/vibey_tools/skills/plugins/semiconductors-and-chip-manufacturing/skills/semi-reference/SKILL.md
requires: ["skill-31-quick-reference-80f36a758c"]
links: []
---

## §32. Method

**§1–§26 → `semi-carriers-doping-junctions-mosfet-and-scaling`, `semi-transistor-architectures-interconnect-memory-and-wafers`, `semi-cleanroom-lithography-deposition-etch-and-cmp`, `semi-integration-yield-metrology-test-and-packaging`, `semi-pcb-assembly-reliability-design-flow-and-economics` rests on settled device physics and mature manufacturing practice** — **MOSFET
operation, the yield model, the lithography ladder, damascene copper, packaging types and
the reliability mechanisms.** ⚠️ **None needed verification; the 60 mV/decade limit is
Boltzmann statistics and Dennard's paper is from 1974.**

**Two searches were run in August 2026**, on **High-NA EUV** and **advanced packaging** —
⚠️ **the first because §11 → `semi-cleanroom-lithography-deposition-etch-and-cmp`'s frontier just moved from R&D into production, the second
because §20 → `semi-integration-yield-metrology-test-and-packaging` has become the industry's binding constraint and that is a structural
reversal.**

**Confidence.** **High** in §5 → `semi-carriers-doping-junctions-mosfet-and-scaling` and §17 → `semi-integration-yield-metrology-test-and-packaging`, which are the sections I'd most want read.
⚠️ **The Dennard-versus-Moore distinction is the single most useful correction here:
"Moore's Law is dead" is wrong in the way people usually mean it, and what actually ended
was Dennard scaling — with the 60 mV/decade subthreshold floor as the specific physical
reason, and multicore and dark silicon as the direct consequences.** ⚠️ **§17 → `semi-integration-yield-metrology-test-and-packaging`'s exponential
yield-versus-area relationship is the second, because it explains chiplets, binning,
product stacks and the reticle limit all at once.** **§5 → `semi-carriers-doping-junctions-mosfet-and-scaling`'s node-naming gotcha is the one
that most often prevents a bad decision.**

**High** on §27.1's production milestone, which comes from ASML's own press release
confirming High-NA reached high-volume manufacturing on Intel 18A on 15 July 2026, and on
the tool specifications reported by Intel.
⚠️ **The genuinely interesting content is the DISAGREEMENT, and I've presented it as an
open economic question rather than picking a winner — TSMC's position that Low-NA double
patterning may still cost less than High-NA single patterning is a serious argument, and
one analysis puts TSMC's likely adoption out around 2029–30.** ⚠️ **Cost figures
($360–400m), the 66% smaller features claim and the ~30% per-patterning-step cost adder are
all from trade reporting and marked as reported.**

**Moderate-to-high** on §27.2, and the confidence is uneven by claim. ⚠️ **The Epoch AI
estimate — roughly 90% of CoWoS and HBM against about 12% of advanced logic dies — is the
best-sourced and most clarifying single datum, and it is explicitly an estimate.**
⚠️ **The capacity numbers are the weak part: sources give TSMC CoWoS 2026 figures ranging
from about 45,000 to 140,000 wafers per month depending on date, scope and whether OSAT is
included, and I have reported the range rather than picking one.** ⚠️ **Most of this
material comes from market-intelligence firms, supply-chain consultancies and investment
outlets with positions, which I've flagged in-section.** **⚠️ The structural claim — that
the constraint has moved from front end to back end — is consistent across every source and
is the part worth carrying.**
