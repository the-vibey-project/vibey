---
id: skill-16-quick-reference-677a52471a
purpose: 16 quick reference
source: src/vibey_tools/skills/plugins/nanotechnology/skills/nano-reference/SKILL.md
requires: ["skill-15-books-14755eb162"]
links: ["skill-17-method-36d1470c34"]
---

## §16. Quick Reference

### 16.1 Equations
```
S/V = 3/r                              surface-to-volume, sphere
T_m(r) = T_m[1 − 2σ/(ΔH·ρ·r)]          Gibbs-Thomson melting depression
E_n = n²h²/(8mL²)                      particle in a box
T ≈ e^(−2κd)                           tunnelling ⚠️ exponential in distance
G₀ = 2e²/h                             conductance quantum
E_C = e²/2C                            charging energy (Coulomb blockade)
CD = k₁λ/NA · DOF = k₂λ/NA²            lithography ⚠️ resolution vs focus
D = k_BT/(6πηr)                        Stokes-Einstein
⟨x²⟩ = 2Dt                             diffusion
Re = ρvL/µ                             ⚠️ ~10⁻⁵ at nanoscale
d = λ/(2NA)                            Abbe limit ~200 nm
```

### 16.2 Picker
| Need | Use |
|---|---|
| Image surface topography, nm | SEM or AFM (§6 → `nano-characterization-materials-and-nanomedicine`) |
| Image internal structure, atomic | ⚠️ **TEM/STEM — destructive prep** (§6 → `nano-characterization-materials-and-nanomedicine`) |
| Size in suspension | DLS ⚠️ (intensity-weighted) (§6 → `nano-characterization-materials-and-nanomedicine`) |
| Surface composition and oxidation state | XPS (§6 → `nano-characterization-materials-and-nanomedicine`) |
| Conformal coating in a tight gap | ⚠️ **ALD** (§3 → `nano-fabrication-and-semiconductor-process`) |
| Vertical sidewalls | ⚠️ **Plasma/RIE, not wet etch** (§3 → `nano-fabrication-and-semiconductor-process`) |
| Sub-10 nm pattern, prototype | E-beam (⚠️ slow) (§3 → `nano-fabrication-and-semiconductor-process`) |
| 5–50 nm periodic pattern at scale | Block copolymer DSA (§4 → `nano-fabrication-and-semiconductor-process`) |
| Monodisperse nanoparticles | ⚠️ **Separate nucleation from growth** (§4 → `nano-fabrication-and-semiconductor-process`) |
| Electronic structure, ~100s of atoms | DFT (⚠️ pick the functional deliberately) (§10.2 → `nano-computational-methods-and-safety`) |
| Accurate bandgap | ⚠️ **Hybrid or GW — not PBE** (§10.2 → `nano-computational-methods-and-safety`) |
| Layered material or molecular crystal | ⚠️ **DFT + dispersion correction** (§10.2 → `nano-computational-methods-and-safety`) |
| MD at near-DFT accuracy, 10⁵+ atoms | ⚠️ **MLIP, fine-tuned, energy-conserving** (§10.3 → `nano-computational-methods-and-safety`) |
| Rare events beyond µs | Enhanced sampling or kMC (§10.4 → `nano-computational-methods-and-safety`) |
| Nanoscale structural scaffold | ⚠️ **DNA origami** (§8 → `nano-characterization-materials-and-nanomedicine`) |
| Deliver nucleic acid in vivo | ⚠️ **LNP with ionizable lipid** (§9 → `nano-characterization-materials-and-nanomedicine`) |

### 16.3 Sanity checklist
- [ ] Is the node name being read as a dimension? (§5.1 → `nano-fabrication-and-semiconductor-process`)
- [ ] Reporting particle size with the measurement method? (§6 → `nano-characterization-materials-and-nanomedicine`)
- [ ] DFT: cutoff and k-points converged? Functional justified? (§10.2 → `nano-computational-methods-and-safety`)
- [ ] DFT: dispersion correction for a layered/molecular system? (§10.2 → `nano-computational-methods-and-safety`)
- [ ] MLIP: energy-conserving architecture? Fine-tuned for the task? (§10.3 → `nano-computational-methods-and-safety`)
- [ ] MLIP predictions validated by DFT before claiming discovery? (§10.3 → `nano-computational-methods-and-safety`)
- [ ] MD: timestep compatible with the fastest vibration? (§10.4 → `nano-computational-methods-and-safety`)
- [ ] Nanoparticle biology: is EPR being assumed? Corona considered? (§9 → `nano-characterization-materials-and-nanomedicine`)
- [ ] Toxicity claim: size, surface chemistry, agglomeration state reported? (§11 → `nano-computational-methods-and-safety`)
- [ ] Is a macroscale force intuition (gravity, inertia) being applied? (§1.2 → `nano-scaling-laws-and-quantum-effects`)

---
