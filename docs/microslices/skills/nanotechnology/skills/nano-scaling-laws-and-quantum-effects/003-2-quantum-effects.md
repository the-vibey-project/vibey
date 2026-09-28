---
id: skill-2-quantum-effects-ddc3acb4aa
purpose: 2 quantum effects
source: src/vibey_tools/skills/plugins/nanotechnology/skills/nano-scaling-laws-and-quantum-effects/SKILL.md
requires: ["skill-1-scaling-laws-d0b5b36f3c"]
links: []
---

## §2. Quantum Effects

### 2.1 Confinement

When a structure is smaller than the charge carrier's natural extent, energy levels
discretize. **Particle in a box**: `E_n = n²h²/(8mL²)` — ⚠️ **note the `1/L²`: energy
rises steeply as the box shrinks.**

**The relevant length is the exciton Bohr radius**: CdSe ~5.6 nm, PbS ~18 nm, Si ~5 nm.
**Below it, the bandgap widens as the particle shrinks:**
```
E_g(r) ≈ E_g(bulk) + h²/(8µr²) − 1.8e²/(4πεε₀r)
```
> **⚠️ GOTCHA — this is why quantum dots are the canonical nanotech demonstration.**
> **The same chemical composition emits different colours purely as a function of
> size.** A 2 nm CdSe dot emits blue; 6 nm emits red. **Nothing changed but the geometry**
> — and that is the cleanest possible illustration that at this scale, size is a material
> property.

**Dimensionality** changes the density of states qualitatively: 3D bulk (`∝ √E`) →
2D quantum well (step function) → 1D wire (⚠️ **van Hove singularities**) → 0D dot
(⚠️ **discrete delta functions — "artificial atoms"**).

### 2.2 Tunnelling and transport

**Tunnelling probability** `T ≈ e^(−2κd)`, with `κ = √(2m(V−E))/ħ`.
⚠️ **The exponential dependence on distance is what makes STM work** — a 1 Å change in tip
height changes current by roughly an order of magnitude, which is where atomic resolution
comes from (§6 → `nano-characterization-materials-and-nanomedicine`).

**⚠️ It's also the leakage mechanism that ended classical transistor scaling**: below ~2 nm
of gate oxide, direct tunnelling current becomes unmanageable, **which is why high-k
dielectrics exist** (§5.2 → `nano-fabrication-and-semiconductor-process`).

**Ballistic transport** when the device is shorter than the mean free path — ⚠️ **no
scattering, so resistance stops depending on length.** **Conductance quantizes** in units
of `G₀ = 2e²/h ≈ 77.5 µS` (~12.9 kΩ per channel). **Coulomb blockade**: when charging
energy `E_C = e²/2C` exceeds `k_BT`, ⚠️ **electrons must transfer one at a time — the basis
of single-electron transistors, and it requires very small C or very low T.**
