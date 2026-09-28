---
id: skill-19-books-and-quick-reference-fd908333d5
purpose: 19 books and quick reference
source: src/vibey_tools/skills/plugins/biology-chemistry-foundations/skills/biochem-reference/SKILL.md
requires: ["skill-18-numbers-57b9afd62a"]
links: ["skill-20-method-355a5c5597"]
---

## §19. Books and Quick Reference

### 19.1 Books

| Author | Work | Why |
|---|---|---|
| **Atkins & de Paula** | ***Physical Chemistry*** | ⚠️ **The standard for §4–§7 → `biochem-thermodynamics-kinetics-and-equilibrium`** |
| **Zumdahl** or **Oxtoby** | *Chemical Principles* | General chemistry, well-explained |
| **Clayden, Greeves & Warren** | ***Organic Chemistry*** | ⚠️ **The best organic textbook written. Mechanism-first, and genuinely readable** |
| **Carey & Sundberg** | *Advanced Organic Chemistry* | The graduate reference |
| **Anslyn & Dougherty** | *Modern Physical Organic Chemistry* | Why mechanisms work |
| **Nelson & Cox** | ***Lehninger Principles of Biochemistry*** | ⚠️ **The biochemistry reference** |
| **Berg, Tymoczko & Stryer** | *Biochemistry* | The main alternative; more structural |
| **Alberts et al.** | ***Molecular Biology of the Cell*** | ⚠️ **§14 → `biochem-biomolecules-cells-and-evolution`, §15 → `biochem-biomolecules-cells-and-evolution`, and the foundation of everything cellular** |
| **Campbell & Reece** | *Biology* | The comprehensive survey |
| **Fersht** | *Structure and Mechanism in Protein Science* | ⚠️ **§11 → `biochem-biomolecules-cells-and-evolution` done properly** |
| **Nicholls & Ferguson** | *Bioenergetics* | ⚠️ **§12 → `biochem-biomolecules-cells-and-evolution`'s chemiosmosis, from the authority** |
| **Futuyma & Kirkpatrick** | *Evolution* | §16 → `biochem-biomolecules-cells-and-evolution` |
| **Silberberg** | *Chemistry: The Molecular Nature of Matter and Change* | Strong on visualization |
| **Pauling** | *The Nature of the Chemical Bond* | Historical, and still clarifying |

**Free and primary**: **LibreTexts** (⚠️ **genuinely good, open, and covers all of this**),
**MIT OpenCourseWare**, **PubChem**, **NIST Chemistry WebBook** (⚠️ **thermodynamic data,
authoritative**), **RCSB PDB**, **KEGG** and **Reactome** (pathways), **BRENDA** (enzyme
kinetics), **UniProt**.

### 19.2 Equations
```
ΔG = ΔH − TΔS                       ΔG = ΔG° + RT ln Q
ΔG° = −RT ln K                      ΔG° = −nFE°
S = k_B ln W                        PV = nRT
k = A e^(−Ea/RT)                    t½ = ln2/k  (first order)
pH = pK_a + log([A⁻]/[HA])          K_w = [H⁺][OH⁻]
E = E° − (0.0592/n) log Q           A = εcl
v = V_max[S]/(K_m+[S])              k_cat/K_m  (catalytic efficiency)
Π = iMRT                            C = kP  (Henry)
```

### 19.3 Reasoning checklist
- [ ] Asked about direction (ΔG) or rate (Ea)? ⚠️ **They're independent** (§4 → `biochem-thermodynamics-kinetics-and-equilibrium`, §5 → `biochem-thermodynamics-kinetics-and-equilibrium`)
- [ ] Using ΔG° where actual concentrations matter? (§4.1 → `biochem-thermodynamics-kinetics-and-equilibrium`)
- [ ] Is the "catalyst" being credited with shifting equilibrium? (§5 → `biochem-thermodynamics-kinetics-and-equilibrium`)
- [ ] Electronegativity difference checked before assigning bond type? (§1.3 → `biochem-atoms-bonding-and-intermolecular-forces`)
- [ ] Lone pairs counted in the VSEPR domain count? (§2.2 → `biochem-atoms-bonding-and-intermolecular-forces`)
- [ ] Conjugate base stability considered for acidity? (§6 → `biochem-thermodynamics-kinetics-and-equilibrium`)
- [ ] E°′ (pH 7) or E° (pH 0) for a biological half-reaction? (§7 → `biochem-thermodynamics-kinetics-and-equilibrium`)
- [ ] Carbocation rearrangement possible? (§8.2 → `biochem-organic-chemistry-and-analytical-methods`)
- [ ] Stereochemical outcome: inversion (Sɴ2) or racemization (Sɴ1)? (§8.2 → `biochem-organic-chemistry-and-analytical-methods`)
- [ ] Is [S] ≫ [E] actually true for Michaelis-Menten? (§11 → `biochem-biomolecules-cells-and-evolution`)
- [ ] NADH (catabolic) or NADPH (anabolic)? (§12.2 → `biochem-biomolecules-cells-and-evolution`)

---
