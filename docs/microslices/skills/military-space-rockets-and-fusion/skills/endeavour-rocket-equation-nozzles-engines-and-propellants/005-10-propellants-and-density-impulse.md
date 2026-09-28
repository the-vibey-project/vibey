---
id: skill-10-propellants-and-density-impulse-5ffc757a7d
purpose: 10 propellants and density impulse
source: src/vibey_tools/skills/plugins/military-space-rockets-and-fusion/skills/endeavour-rocket-equation-nozzles-engines-and-propellants/SKILL.md
requires: ["skill-9-turbomachinery-engine-cycles-and-cooling-ca34e541a4"]
links: ["skill-quick-reference-45bf6d3664"]
---

## §10 Propellants and density impulse

| Combination | Isp_vac (s) | ρ_bulk (kg/m³) | T_c (K) | Notes |
|---|---|---|---|---|
| LOX/LH₂ | 450–465 | ~360 | 3,200 | Best Isp, worst density |
| LOX/CH₄ | 360–380 | ~830 | 3,500 | Clean, ISRU-able |
| LOX/RP-1 | 340–360 | ~1,030 | 3,700 | Dense, cokes |
| N₂O₄/MMH | 320–340 | ~1,190 | 3,400 | Hypergolic, toxic |
| APCP (solid) | 250–290 | ~1,800 | 3,000 | No shutdown |

> **DENSITY IMPULSE — THE METRIC PEOPLE OMIT.** I_ρ = Isp × ρ_bulk measures **impulse per unit tank
> volume**. LOX/LH₂: 450 × 0.36 = **162** (lowest). LOX/RP-1: 350 × 1.03 = **361** (more than double
> hydrogen). This is the quantitative reason **hydrogen loses on first stages**: the tank volume — and
> therefore tank mass, insulation mass and aerodynamic drag — swamps the Isp advantage low in the
> trajectory. **Hydrogen wins where Δv is high and structure is a smaller fraction: upper stages and
> deep space.**

### Cryogenic realities

- LH₂ boils at **20.3 K**, LOX at **90.2 K**, LCH₄ at **111.7 K**.
- Methane and oxygen being **within ~20 K of each other** permits **common-bulkhead tanks and shared
  insulation** — a real structural advantage that is part of why methane became popular. (The other
  part is that methalox is the combination Martian ISRU can actually make; §30 →
  `endeavour-the-martian-environment-and-in-situ-resources`.)
- Hydrogen's 20 K requires **vacuum-jacketed or foam insulation**, and **boil-off makes long coast
  phases expensive**.

### LOX cleanliness

**A fingerprint in a LOX line is an ignition source.** LOX compatibility rules out most organics and
requires scrupulous cleanliness.
