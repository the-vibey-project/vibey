---
id: skill-15-generative-models-52158818bf
purpose: 15 generative models
source: src/vibey_tools/skills/plugins/medicine-design-software-development/skills/drugdev-qsar-admet-generative-models-and-validation/SKILL.md
requires: ["skill-14-admet-prediction-ac76d820b0"]
links: ["skill-16-active-learning-and-the-dmta-loop-fe0fe4522c"]
---

## §15. Generative Models

**⚠️ De novo design — proposing new molecules rather than filtering existing ones.**
```
APPROACHES  VAEs · GANs · autoregressive (SMILES/SELFIES) ·
   ⚠️ reinforcement learning against a scoring function ·
   ⚠️ diffusion models (increasingly, especially 3D structure-based)
⚠️ CONDITIONING  on a target pocket, on desired properties,
   scaffold-constrained, fragment growing/linking
```
> **⚠️ GOTCHA — generation is not the hard part; SCORING is.** ⚠️ **A generative model
> optimizes whatever objective you give it, and if that objective is a docking score
> (§10 → `drugdev-protein-structure-docking-and-molecular-dynamics`) or a QSAR model (§13), the generator will find that function's failure modes.**
> **⚠️ This is reward hacking with molecules — you get compounds that score brilliantly
> and are inactive, unstable or unmakeable.**
> **⚠️ Therefore: SYNTHESIZABILITY constraints (SA score, retrosynthesis-aware generation,
> or generating only from purchasable building blocks) are not a nicety.** ⚠️ **And
> "novelty" metrics are nearly meaningless — it is trivial to generate novel molecules and
> hard to generate novel USEFUL ones.**

**⚠️ Retrosynthesis prediction and computer-aided synthesis planning** (⚠️ **ASKCOS,
AiZynthFinder, commercial tools**) **close the loop, and ⚠️ they are the practical gate on
whether a designed molecule can actually be made.**

---
