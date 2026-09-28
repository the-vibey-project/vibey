---
id: skill-14-what-actually-moved-ed57ad3e71
purpose: 14 what actually moved
source: src/vibey_tools/skills/plugins/nanotechnology/skills/nano-reference/SKILL.md
requires: ["skill-13-numbers-87fd847990"]
links: ["skill-15-books-14755eb162"]
---

## §14. What Actually Moved

### 14.1 The leading-edge node — verified August 2026

**⚠️ Verified directly against TSMC's technology page**, because secondary sources
conflicted:
- **TSMC N2 started volume production in 4Q25**, featuring **first-generation nanosheet
  (GAA) transistors**, plus low-resistance RDL and **super high-performance MiM
  capacitors** in the power delivery network.
- ⚠️ **N2 does NOT include backside power delivery.** TSMC's **A16** is the node that
  "integrates leading nanosheet transistors with innovative backside power rail solution,"
  and **A12** is described as the *second* generation of that backside rail.
  **⚠️ Multiple secondary sources incorrectly attribute backside power to N2P — including
  sources contradicting each other within the same month. Do not trust node feature lists
  that aren't from the foundry.**
- **Intel 18A** pairs **RibbonFET** (its GAA) with **PowerVia** (its backside power),
  taking the more aggressive combined path; **Samsung SF2** is frontside, with the backside
  variant roadmapped later.
- **Reported N2 yields** in the 65–75% range — ⚠️ **these are trade-press figures, not
  foundry disclosures, and yield numbers are among the least reliable public data in this
  industry.**
- ⚠️ **First-generation GAA does not require High-NA EUV.** High-NA is a later
  overlay-and-pitch tool.

**⚠️ The synthesis worth keeping**: 2 nm is **not a single breakthrough but the industrial
integration of GAA nanosheets, advanced EUV, refined metallization, and power-delivery
changes** — and the hard part is **a repeatable line where scanner, mask, resist, etch,
metrology, transistor, interconnect, package and power all agree.**

### 14.2 Foundation-model interatomic potentials
**The genuine methodological shift** (§10.3 → `nano-computational-methods-and-safety`): universal MLIPs trained on large DFT datasets
— **MACE-MP-0** (Materials Project trajectories), **MatterSim** (⚠️ **reported 17 million
DFT-labelled structures**), **CHGNet, GRACE, eSEN, UMA**. **Generative structure models**
(MatterGen, DiffCSP, Chemeleon) propose candidates; ⚠️ **GNoME reported over 2.2 million
new stable materials by combining graph networks with active-learning-driven DFT
validation** — **note that the DFT validation is part of the claim, which is the right
pattern.**

**⚠️ The honest caveats, from the literature itself**: foundation models "do not yet achieve
the accuracy required to predict reaction barriers, phase transitions, and material
stability" without fine-tuning; **direct-force architectures fail to conserve energy in
MD**; and **benchmark rank does not imply physical soundness.** **Fine-tuning tutorials and
frozen-transfer-learning methods are now mature enough to be standard practice.**

---
