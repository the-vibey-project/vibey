---
id: skill-1-scaling-laws-d0b5b36f3c
purpose: 1 scaling laws
source: src/vibey_tools/skills/plugins/nanotechnology/skills/nano-scaling-laws-and-quantum-effects/SKILL.md
requires: ["skill-0-routing-b60e061b68"]
links: ["skill-2-quantum-effects-ddc3acb4aa"]
---

## §1. Scaling Laws

### 1.1 Surface-to-volume

For a sphere: `S/V = 3/r`. ⚠️ **Halve the radius, double the ratio.**
```
1 cm cube      surface fraction ~0.00000001% of atoms
100 nm particle    ~1% of atoms are surface
10 nm particle     ~10%
2 nm particle      ⚠️ ~50% of atoms are ON THE SURFACE
```
**⚠️ At 2 nm, "bulk" is a minority phase.** Surface atoms are undercoordinated, higher in
energy, and chemically reactive — which is why **nanoparticle catalysis works**, why
**nanoparticles sinter and aggregate spontaneously**, and why **gold — famously inert in
bulk — is an excellent catalyst below ~5 nm.**

**Melting point depression** (Gibbs–Thomson):
```
T_m(r) = T_m(bulk)·[1 − 2σ_sl/(ΔH_f·ρ·r)]
```
⚠️ **Gold melts at 1064 °C in bulk and near 300 °C at 2 nm.** The same equation governs
nanoparticle sintering, and it is why nanoparticle catalysts degrade thermally.

### 1.2 ⚠️ Which forces matter

```
Force                Scales as     At 1 µm     At 10 nm
Gravity / weight        L³         negligible   ⚠️ utterly irrelevant
Surface tension         L¹         dominant     dominant
Van der Waals        ~L¹ (spheres) significant  ⚠️ dominant
Electrostatic         varies       significant  significant
Brownian motion       ⚠️ ∝ 1/√(mass)  strong    ⚠️ overwhelming
```
**⚠️ The consequences invert macroscale engineering:**
- **Stiction, not gravity, is the enemy.** MEMS devices fail by surfaces sticking
  permanently — ⚠️ **an assembled nanostructure doesn't fall apart, it refuses to come
  apart.**
- **⚠️ Brownian motion is not noise at this scale — it's the dominant transport
  mechanism.** `⟨x²⟩ = 2Dt` (Einstein), with `D = k_BT/(6πηr)` (Stokes-Einstein).
  **A 10 nm particle in water diffuses its own diameter in microseconds.**
- **⚠️ Reynolds number is tiny** (`Re = ρvL/µ`, ~10⁻⁵ or less) — **flow is entirely
  laminar and viscous, inertia is meaningless, and motion stops the instant force is
  removed.** Purcell's point: **a bacterium swimming is like a human in honey**, and
  reciprocal motion produces zero net displacement.
- **Diffusion beats convection**: mixing time `t ≈ L²/D`, so ⚠️ **at small L, diffusion is
  fast and stirring is pointless.**

---
