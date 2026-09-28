---
id: skill-17-method-36d1470c34
purpose: 17 method
source: src/vibey_tools/skills/plugins/nanotechnology/skills/nano-reference/SKILL.md
requires: ["skill-16-quick-reference-677a52471a"]
links: []
---

## §17. Method

**§1–§4 → `nano-scaling-laws-and-quantum-effects`, `nano-fabrication-and-semiconductor-process`, §6–§9 → `nano-characterization-materials-and-nanomedicine` and §11 → `nano-computational-methods-and-safety` rest on standard references** — Israelachvili for surface forces,
Ozin for nanochemistry, Plummer for fabrication, Frenkel & Smit and Martin for simulation
theory — **and on physics that has been settled for decades.** ⚠️ **None of that was
web-verified, and none needed to be.**

**Two searches were run in August 2026**, on the two areas that genuinely moved: the
**leading-edge semiconductor node** and **ML interatomic potentials**.

**⚠️ The node section required a primary-source check and it changed the answer.**
Secondary sources contradicted each other on whether N2P carries backside power delivery —
including two sources from the same month asserting opposite things — so I fetched
**TSMC's own technology page**, which states N2 volume production in 4Q25 and attributes
the backside power rail to **A16** (with A12 as its second generation). **§14.1 reflects
the foundry, not the trade press**, and I have flagged the discrepancy rather than silently
picking a side.

**For §10.3 → `nano-computational-methods-and-safety` and §14.2**: the *Journal of Chemical Physics* MACE-MP-0 foundation-model
paper, the *Nature Reviews Chemistry* review of foundation models for atomistic simulation,
*npj Computational Materials* on frozen transfer learning and on GRACE, a 2026 *Advanced
Energy Materials* review for the benchmark and energy-conservation observations, and a 2026
AIP tutorial on fine-tuning universal MLIPs.

**Confidence.** **High** in §1–§9 → `nano-scaling-laws-and-quantum-effects`, `nano-fabrication-and-semiconductor-process`, `nano-characterization-materials-and-nanomedicine` and §11 → `nano-computational-methods-and-safety` — settled physics, with numbers as representative
ranges. **High** in §14.1's TSMC facts (primary source) and in §10.3 → `nano-computational-methods-and-safety`'s methodological
caveats, which come from the peer-reviewed literature and are stated there explicitly
rather than being my inference.

⚠️ **Lower confidence, flagged in place, on two things.** **Yield figures** in §14.1 are
trade-press estimates — **foundries do not disclose yields, and these numbers vary widely
between sources.** And ⚠️ **the GNoME "2.2 million stable materials" figure is a
count of computational predictions with DFT validation, not of synthesized materials** —
the distinction matters enormously and is frequently collapsed in coverage. **§12's
misconception entries about MLIPs and DFT are the ones most likely to save someone a
wasted month.**
