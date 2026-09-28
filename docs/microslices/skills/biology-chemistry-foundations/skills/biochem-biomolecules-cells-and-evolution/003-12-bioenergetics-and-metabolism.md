---
id: skill-12-bioenergetics-and-metabolism-c28340dba3
purpose: 12 bioenergetics and metabolism
source: src/vibey_tools/skills/plugins/biology-chemistry-foundations/skills/biochem-biomolecules-cells-and-evolution/SKILL.md
requires: ["skill-11-enzymes-687f0788cc"]
links: ["skill-13-membranes-and-transport-d6b5b11dd5"]
---

## §12. Bioenergetics and Metabolism

### 12.1 ATP and coupling
**ATP hydrolysis ΔG°′ ≈ −30.5 kJ/mol**; ⚠️ **in cells, with actual concentrations, ΔG is
closer to −50 kJ/mol** (§4.1 → `biochem-thermodynamics-kinetics-and-equilibrium` — Q matters).

> **⚠️ GOTCHA — there is no "high-energy phosphate bond."** The energy doesn't reside in
> the bond; it comes from the **whole reaction**: charge repulsion relief in ATP,
> **resonance stabilization of the released phosphate**, and favourable solvation of the
> products. **Bond breaking always costs energy.** The teaching shorthand is actively
> misleading.

**⚠️ ATP is a currency, not a store.** The body turns over roughly its own body weight in
ATP per day while holding only ~50 g at any moment.

### 12.2 The pathways
```
GLYCOLYSIS      glucose → 2 pyruvate | 2 ATP net, 2 NADH | cytosol, anaerobic-capable
                ⚠️ Investment phase costs 2 ATP; payoff yields 4
PYRUVATE OX.    pyruvate → acetyl-CoA | 1 NADH, 1 CO₂ each | ⚠️ irreversible in animals
CITRIC ACID     acetyl-CoA → 2 CO₂ | 3 NADH, 1 FADH₂, 1 GTP per turn
OXIDATIVE PHOS. NADH/FADH₂ → ~2.5 / ~1.5 ATP | ⚠️ ~30–32 ATP per glucose total
```
**⚠️ The old "36–38 ATP" figure is outdated.** Modern estimates are ~30–32, because the
proton-to-ATP stoichiometry isn't integral and transport costs protons.

**⚠️ Chemiosmotic hypothesis (Mitchell, 1961)** — the key insight, and it was resisted for
years: **the electron transport chain pumps protons across the inner mitochondrial
membrane, creating an electrochemical gradient (proton-motive force), and ATP synthase is
a rotary motor driven by proton flow back down it.** **Energy is stored as a gradient, not
as a chemical intermediate.** ⚠️ **Uncouplers (DNP) dissipate the gradient — respiration
continues, ATP synthesis stops, and the energy leaves as heat.**

**Other pathways**: pentose phosphate (⚠️ **NADPH for biosynthesis and ribose for
nucleotides — a different reducing currency from NADH, and the distinction matters**),
β-oxidation, gluconeogenesis (⚠️ **not simply reverse glycolysis — it bypasses the three
irreversible steps**), glycogen metabolism, urea cycle, photosynthesis.

**⚠️ Catabolism is oxidative and uses NAD⁺; anabolism is reductive and uses NADPH.**
Keeping the two pools separate lets a cell run both directions simultaneously.

---
