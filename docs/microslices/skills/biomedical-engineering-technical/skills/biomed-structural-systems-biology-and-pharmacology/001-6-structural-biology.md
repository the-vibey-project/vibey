---
id: skill-6-structural-biology-0fb8c24163
purpose: 6 structural biology
source: src/vibey_tools/skills/plugins/biomedical-engineering-technical/skills/biomed-structural-systems-biology-and-pharmacology/SKILL.md
requires: []
links: ["skill-7-systems-biology-4bf74f83b0"]
---

## §6. Structural Biology

**Protein structure**: primary (sequence) → secondary (α-helix, β-sheet, from backbone
φ/ψ angles — ⚠️ **Ramachandran plot shows the allowed regions**) → tertiary → quaternary.

**Determination**: **X-ray crystallography** (⚠️ **resolution in Å; requires crystals, and
the phase problem**), **cryo-EM** (⚠️ **the resolution revolution — now routinely
sub-3 Å, no crystals needed**), **NMR** (solution state, size-limited).

**Prediction**: **AlphaFold2/3** changed the field — ⚠️ **read the confidence metrics
properly. pLDDT is per-residue confidence (>90 very high, <50 likely disordered); PAE is
the predicted aligned error between residue pairs and is what tells you whether relative
domain positions are trustworthy.** **A high-pLDDT structure with high inter-domain PAE
means good domains, unreliable arrangement.**

**⚠️ And the standing caveats**: predicted structures are **single static conformations**;
they do not give you the conformational ensemble, ligand-bound states, or the effects of
point mutations reliably.

**Molecular dynamics**: integrate Newton's equations with a **force field** (AMBER,
CHARMM, OPLS) at **~2 fs timesteps** — ⚠️ **which is the fundamental problem: biologically
interesting events take microseconds to milliseconds, i.e. 10⁹–10¹² steps.** Enhanced
sampling (replica exchange, metadynamics, umbrella sampling) exists to bridge it.
**Docking** (AutoDock Vina, Glide) for binding pose; ⚠️ **scoring functions predict pose
much better than they predict affinity.**

---
