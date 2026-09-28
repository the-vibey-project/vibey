---
id: skill-6-propellants-cd15890d4a
purpose: 6 propellants
source: src/vibey_tools/skills/plugins/rocket-science/skills/rocket-turbomachinery-cooling-and-propellants/SKILL.md
requires: ["skill-5-heat-transfer-and-cooling-8143ab0d31"]
links: []
---

## §6. Propellants

**[DURABLE] The physics that determines choice** (see §2.1 → `rocket-equation-nozzles-and-combustion` — it's `√(T_c/M_w)` plus
density):

| Combination | Isp_vac (s) | ρ_bulk (kg/m³) | T_c (K) | O/F | Notes |
|---|---|---|---|---|---|
| LOX/LH₂ | 450–465 | ⚠️ **~360** | 3,200 | 5.5–6.0 | Best Isp, worst density |
| LOX/CH₄ | 360–380 | ~830 | 3,500 | 3.4–3.8 | Clean, ISRU-able |
| LOX/RP-1 | 340–360 | ~1,030 | 3,700 | 2.3–2.7 | Dense, cokes |
| N₂O₄/MMH | 320–340 | ~1,190 | 3,400 | 1.9–2.2 | Hypergolic, toxic |
| LOX/UDMH | 340–350 | ~1,000 | 3,400 | 1.9 | — |
| APCP (solid) | 250–290 | ~1,800 | 3,000 | — | No shutdown |
| H₂O₂/RP-1 | 300–320 | ~1,250 | 2,900 | 7–8 | Non-toxic monoprop option |

> **⚠️ GOTCHA — density impulse is the metric people omit.**
> `I_ρ = Isp × ρ_bulk`. It measures **impulse per unit tank volume**, and for a
> volume-constrained (rather than mass-constrained) stage it matters more than Isp.
>
> ```
> LOX/LH₂:  450 × 0.36 = 162    ⚠️ lowest
> LOX/CH₄:  370 × 0.83 = 307
> LOX/RP-1: 350 × 1.03 = 361    ⚠️ more than double hydrogen
> N₂O₄/MMH: 330 × 1.19 = 393
> ```
> **This is the quantitative reason hydrogen loses on first stages.** The tank volume —
> and therefore tank mass, insulation mass, and aerodynamic drag — swamps the Isp
> advantage low in the trajectory where mass ratio matters less. **Hydrogen wins where Δv
> is high and structure is a smaller fraction: upper stages and deep space.**

**Cryogenic realities**: LH₂ boils at **20.3 K**, LOX at **90.2 K**, LCH₄ at **111.7 K**.
⚠️ **Methane and oxygen being within ~20 K of each other permits common-bulkhead tanks and
shared insulation** — a real structural advantage that is part of why methane became
popular. **Hydrogen's 20 K requires vacuum-jacketed or foam insulation, and boil-off makes
long coast phases expensive.** **Hydrogen embrittlement** attacks many steels;
**LOX compatibility** rules out most organics and requires scrupulous cleanliness —
⚠️ **a fingerprint in a LOX line is an ignition source.**
