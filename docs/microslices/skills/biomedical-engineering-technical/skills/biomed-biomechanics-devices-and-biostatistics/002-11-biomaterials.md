---
id: skill-11-biomaterials-5d07363d2e
purpose: 11 biomaterials
source: src/vibey_tools/skills/plugins/biomedical-engineering-technical/skills/biomed-biomechanics-devices-and-biostatistics/SKILL.md
requires: ["skill-10-biomechanics-5edaa27425"]
links: ["skill-12-tissue-engineering-586d86e0b2"]
---

## §11. Biomaterials

**Classes and their trade-offs:**

| Material | Modulus | ⚠️ Note |
|---|---|---|
| **316L stainless** | 200 GPa | Cheap; ⚠️ **stress shielding, nickel release** |
| **Ti-6Al-4V** | ⚠️ **110 GPa** | **Closest to bone of the metals; excellent osseointegration** |
| **CoCr** | 210 GPa | Wear-resistant bearing surfaces |
| **UHMWPE** | 1 GPa | ⚠️ **Bearing surface; wear particles drive osteolysis** |
| **PEEK** | 3–4 GPa | ⚠️ **Radiolucent, bone-like modulus; bioinert (doesn't bond)** |
| **PLA/PGA/PLGA** | 1–4 GPa | ⚠️ **Resorbable; degradation rate tunable by copolymer ratio** |
| **Hydroxyapatite** | 80–110 GPa | Bioactive, brittle; a coating more than a bulk material |
| **Bioglass 45S5** | 35 GPa | ⚠️ **Bonds chemically to bone** |
| **Hydrogels (PEG, alginate)** | ⚠️ **kPa** | Soft tissue and cell encapsulation |

**⚠️ Stress shielding is the recurring failure mechanism**: a 200 GPa implant next to
20 GPa bone carries the load, the bone unloads, and Wolff's law resorbs it (§10).
**Modulus matching is a first-order design requirement, not a refinement.**

**Biocompatibility** is graded: **bioinert** (fibrous encapsulation), **bioactive**
(chemical bonding — bioglass, HA), **bioresorbable** (replaced by tissue).
**⚠️ The foreign body response is the default outcome**: protein adsorption within seconds
→ acute inflammation → macrophage/foreign body giant cells → **fibrous capsule**.
**That capsule is why implanted sensors drift and fail** (§13).

**Degradation**: PLGA hydrolyses; ⚠️ **the acidic degradation products can cause local
inflammation, and bulk erosion can produce a sudden mechanical failure rather than a
gradual one.**

---
