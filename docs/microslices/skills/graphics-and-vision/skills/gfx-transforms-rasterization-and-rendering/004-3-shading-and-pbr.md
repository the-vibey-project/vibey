---
id: skill-3-shading-and-pbr-9a061209f6
purpose: 3 shading and pbr
source: src/vibey_tools/skills/plugins/graphics-and-vision/skills/gfx-transforms-rasterization-and-rendering/SKILL.md
requires: ["skill-2-rasterization-330f988324"]
links: ["skill-4-ray-tracing-and-the-rendering-equation-0089667957"]
---

## §3. Shading and PBR

**The BRDF** `f_r(ω_i, ω_o)` describes how light scatters at a surface. ⚠️ **A physically
valid BRDF must obey reciprocity (`f_r(ω_i,ω_o) = f_r(ω_o,ω_i)`) and energy conservation
(it cannot reflect more than it receives).**

**Legacy models**: Lambert diffuse (`n·l`), Phong and Blinn-Phong specular —
⚠️ **not energy-conserving and not reciprocal, but cheap and still everywhere.**

**Modern microfacet PBR** — the standard, built as `D · F · G / (4 (n·l)(n·v))`:
- **D — normal distribution function** (⚠️ **GGX/Trowbridge-Reitz won because its long
  tail matches measured materials far better than Beckmann**).
- **F — Fresnel** (⚠️ **Schlick's approximation; reflectance rises to 1 at grazing angles
  for every material, which is the single most important visual cue PBR added**).
- **G — geometry/shadowing-masking term** (Smith).

**⚠️ The parameterization that won**: **base colour, metallic, roughness**, plus normal,
AO, and emissive. **Metallic is a near-binary switch** — metals have no diffuse and tinted
specular; dielectrics have diffuse and ~4% white specular. ⚠️ **Intermediate metallic
values are physically meaningless and exist only for texture blending at material
boundaries.**

**IBL (image-based lighting)**: prefiltered environment maps + a split-sum approximation
BRDF LUT. **Spherical harmonics** for low-frequency irradiance — ⚠️ **9 coefficients
capture diffuse environment lighting almost exactly, which is why SH is everywhere.**

---
