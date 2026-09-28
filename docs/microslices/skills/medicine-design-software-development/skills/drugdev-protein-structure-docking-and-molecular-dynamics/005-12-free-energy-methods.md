---
id: skill-12-free-energy-methods-ed4e55e806
purpose: 12 free energy methods
source: src/vibey_tools/skills/plugins/medicine-design-software-development/skills/drugdev-protein-structure-docking-and-molecular-dynamics/SKILL.md
requires: ["skill-11-molecular-dynamics-705ed12bb0"]
links: []
---

## §12. Free Energy Methods

**⚠️ The most accurate physics-based affinity predictions available, and the most
expensive.**
```
⚠️ FEP / TI  alchemical transformation between two ligands.
   ⚠️ RELATIVE binding free energy is the practical workhorse —
   reported accuracy often around 1 kcal/mol for congeneric series
⚠️ ABFE  absolute binding free energy — harder, less reliable
MM/PBSA · MM/GBSA  ⚠️ cheaper, much less reliable, and widely
   over-trusted in the literature
```
**⚠️ Where FEP fits in practice**: ⚠️ **lead optimization within a congeneric series where
you already have a good structure** — **prioritizing which of 50 analogues to synthesize.**
**⚠️ It is not a screening tool and it does not rescue a wrong binding mode.**
**⚠️ 1 kcal/mol ≈ a factor of ~5 in affinity at room temperature** — ⚠️ **useful context for
what "accurate to 1 kcal/mol" actually buys you.**

---

# PART IV — MACHINE LEARNING
