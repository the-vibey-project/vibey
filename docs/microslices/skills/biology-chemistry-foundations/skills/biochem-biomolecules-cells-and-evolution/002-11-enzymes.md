---
id: skill-11-enzymes-687f0788cc
purpose: 11 enzymes
source: src/vibey_tools/skills/plugins/biology-chemistry-foundations/skills/biochem-biomolecules-cells-and-evolution/SKILL.md
requires: ["skill-10-biomolecules-4b1d8c57b8"]
links: ["skill-12-bioenergetics-and-metabolism-c28340dba3"]
---

## §11. Enzymes

**⚠️ Enzymes lower ΔG‡ (§5 → `biochem-thermodynamics-kinetics-and-equilibrium`). They do not change ΔG, K, or equilibrium position.** They
accelerate forward and reverse equally.

**Catalytic strategies**: **proximity and orientation** (⚠️ **a large effective
concentration effect**), **acid-base catalysis**, **covalent catalysis**, **metal ion
catalysis**, **electrostatic stabilization**, and ⚠️ **transition-state stabilization —
which is the deepest one. An enzyme binds the transition state more tightly than the
substrate**, and that differential binding *is* the catalysis. **Transition-state analogues
are therefore potent inhibitors, and this is a real drug-design principle.**

**Michaelis-Menten**:
```
v = V_max[S]/(K_m + [S])            V_max = k_cat[E]_T
K_m = [S] at half V_max             ⚠️ an inverse proxy for affinity, with caveats
k_cat/K_m = catalytic efficiency    ⚠️ the number to compare enzymes by
```
**⚠️ Derived under the quasi-steady-state assumption, requiring [S] ≫ [E]** — routinely
violated inside cells, where many enzymes and substrates are at comparable concentration.

**⚠️ The diffusion limit is ~10⁸–10⁹ M⁻¹s⁻¹**, and enzymes approaching it (triosephosphate
isomerase, catalase, carbonic anhydrase) are called **catalytically perfect** — every
encounter produces reaction, and further improvement is physically impossible.

**Inhibition** — ⚠️ **and the diagnostic pattern is the point:**
```
Competitive       binds active site      K_m ↑   V_max unchanged   (surmountable by [S])
Uncompetitive     binds ES complex       K_m ↓   V_max ↓
Noncompetitive    binds E and ES         K_m —   V_max ↓
Mixed             both, unequally        both change
Irreversible      covalent               ⚠️ V_max ↓, not surmountable
```
**Regulation**: **allostery** (⚠️ **cooperative, sigmoidal kinetics — Hill equation; MWC
and KNF models**), covalent modification (⚠️ **phosphorylation is the dominant switch**),
proteolytic activation (zymogens), and feedback inhibition.

---
