---
id: skill-4-relativity-73dd6ae7cf
purpose: 4 relativity
source: src/vibey_tools/skills/plugins/fundamental-physics/skills/physics-relativity-black-holes-and-gravitational-waves/SKILL.md
requires: []
links: ["skill-5-black-holes-3ff236d34b"]
---

## §4. Relativity

### 4.1 Special relativity

**Two postulates**: physics is identical in all inertial frames; `c` is invariant.
Everything follows.

**Minkowski interval** — the invariant: `ds² = −c²dt² + dx² + dy² + dz²`.
⚠️ **The minus sign is the whole of relativity.** Timelike (`ds² < 0`), null (`= 0`),
spacelike (`> 0`) separation determines causal structure.

**Lorentz transformations** with `γ = 1/√(1−v²/c²)`: time dilation, length contraction,
relativity of simultaneity. **Four-vectors**: `p^μ = (E/c, **p**)`, with
`p^μp_μ = −m²c²` giving `E² = (pc)² + (mc²)²`.

⚠️ **Note the massless case**: `E = pc`. Photons carry momentum without mass. **And "relativistic
mass" is a deprecated concept** — mass is the invariant `m`, and treating it as
velocity-dependent causes more confusion than it resolves.

### 4.2 General relativity

**[DURABLE] The equivalence principle is the seed**: locally, free-fall is
indistinguishable from inertial motion — **gravitational and inertial mass are the same
thing.** ⚠️ **Therefore gravity is not a force; it is the geometry of spacetime, and
freely-falling bodies follow geodesics — the straightest available paths.**

**The apparatus:**
```
Metric:        ds² = g_μν dx^μ dx^ν
Christoffel:   Γ^λ_μν = ½g^λσ(∂_μ g_σν + ∂_ν g_σμ − ∂_σ g_μν)
Geodesic:      d²x^λ/dτ² + Γ^λ_μν (dx^μ/dτ)(dx^ν/dτ) = 0
Riemann:       R^ρ_σμν = ∂_μΓ^ρ_νσ − ∂_νΓ^ρ_μσ + Γ^ρ_μλΓ^λ_νσ − Γ^ρ_νλΓ^λ_μσ
Ricci:         R_μν = R^λ_μλν          Scalar: R = g^μν R_μν
```

**The Einstein field equations (1915):**
```
G_μν + Λg_μν = (8πG/c⁴) T_μν       where G_μν = R_μν − ½R g_μν
```
**Wheeler's summary is exactly right: matter tells spacetime how to curve; spacetime tells
matter how to move.**

⚠️ **These are ten coupled nonlinear PDEs.** The nonlinearity is physical, not
technical — **gravitational energy itself gravitates**, which is why there's no
superposition principle and why exact solutions are rare and precious.

**`G_μν` is divergence-free by the Bianchi identities** (`∇^μG_μν = 0`), which **forces**
`∇^μT_μν = 0` — ⚠️ **local energy-momentum conservation is a consequence of the geometry,
not an extra postulate.**

**Classical tests, all passed**: perihelion precession of Mercury (43″/century — ⚠️ **a
retrodiction, calculated before publication and the reason Einstein knew he was right**),
light deflection (1.75″ at the solar limb, twice the Newtonian value), gravitational
redshift, Shapiro delay, frame dragging (Gravity Probe B), and **binary pulsar orbital
decay matching GR's gravitational-wave prediction to ~0.1%.**

---
