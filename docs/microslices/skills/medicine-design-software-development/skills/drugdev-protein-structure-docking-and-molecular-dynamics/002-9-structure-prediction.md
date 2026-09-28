---
id: skill-9-structure-prediction-235c3dc197
purpose: 9 structure prediction
source: src/vibey_tools/skills/plugins/medicine-design-software-development/skills/drugdev-protein-structure-docking-and-molecular-dynamics/SKILL.md
requires: ["skill-8-protein-structure-c7160378f2"]
links: ["skill-10-docking-e5b9961981"]
---

## §9. ⚠️ Structure Prediction

**⚠️ AlphaFold2 and successors were a genuine breakthrough** — ⚠️ **reported pLDDT above 90
for well-determined regions, and the AlphaFold DB made predicted structures available at
proteome scale.** **⚠️ AlphaFold3 and equivalents extend to complexes including
protein-ligand.**
> **⚠️ GOTCHA — "we solved protein structure" overstates it in ways that matter for drug
> design specifically.** ⚠️ **Predicted structures are typically APO-like and represent one
> conformation; docking into AlphaFold models has repeatedly been shown to perform WORSE
> than docking into experimental holo structures** — **because side chains in the pocket
> are not in their ligand-bound arrangement.**
> **⚠️ pLDDT is a CONFIDENCE score, not an accuracy guarantee, and low-pLDDT regions are
> frequently intrinsically disordered rather than merely uncertain.**
> **⚠️ Structure prediction did not solve binding affinity, conformational ensembles, or
> the effect of mutations on function.**

---
