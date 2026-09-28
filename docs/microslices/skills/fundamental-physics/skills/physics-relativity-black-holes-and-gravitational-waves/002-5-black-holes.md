---
id: skill-5-black-holes-3ff236d34b
purpose: 5 black holes
source: src/vibey_tools/skills/plugins/fundamental-physics/skills/physics-relativity-black-holes-and-gravitational-waves/SKILL.md
requires: ["skill-4-relativity-73dd6ae7cf"]
links: ["skill-6-gravitational-waves-2214faac0b"]
---

## §5. Black Holes

### 5.1 Schwarzschild

The unique static spherically-symmetric vacuum solution (**Birkhoff's theorem** —
⚠️ **which also means a spherically pulsating star emits no gravitational waves**):
```
ds² = −(1 − r_s/r)c²dt² + (1 − r_s/r)^(−1) dr² + r²dΩ²,     r_s = 2GM/c²
```
**⚠️ The `r = r_s` singularity is a coordinate artifact, not physics** — curvature
invariants are finite there. Kruskal–Szekeres coordinates remove it. **The `r = 0`
singularity is real**: curvature diverges.

**⚠️ Nothing locally special happens at the horizon for an infalling observer.** The
horizon is a *global* causal boundary, defined by where the future light cones tip inward.
**An infalling observer crosses in finite proper time and notices nothing**; a distant
observer sees them asymptotically freeze and redshift away. **Both descriptions are
correct.**

**Photon sphere at `1.5 r_s`**; **ISCO at `3 r_s`** — ⚠️ **the innermost stable circular
orbit is why accretion discs have an inner edge and why ~6% (Schwarzschild) to ~42%
(maximal Kerr) of rest mass can be radiated**, making accretion the most efficient
energy-release mechanism known short of annihilation.

### 5.2 Kerr and the no-hair theorem

Rotating black holes (Kerr, 1963) have an **ergosphere** where frame-dragging makes static
observers impossible — ⚠️ **and the Penrose process can extract rotational energy from it**,
the likely engine of relativistic jets via Blandford–Znajek.

**No-hair theorem**: a stationary black hole is fully described by **mass, angular
momentum, and charge**. ⚠️ **Nothing else survives.** This is what makes black hole
information (§5.4) a paradox rather than a curiosity.

### 5.3 Singularities
**Penrose–Hawking theorems**: under reasonable energy conditions, singularities are
generic, not artifacts of symmetry. ⚠️ **Correctly read, this is a statement that GR
predicts its own breakdown** (§12 → `physics-measurement-problem-and-quantum-gravity`).

### 5.4 Black hole thermodynamics

**[DURABLE] The deepest known clue about quantum gravity.**
```
T_H = ħc³/(8πGMk_B)              Hawking temperature
S_BH = k_B A/(4ℓ_P²)             Bekenstein–Hawking entropy
```
**⚠️ Read those two equations carefully — they contain `ħ`, `c`, `G`, and `k_B`
simultaneously.** They are the only well-established results that involve quantum
mechanics, relativity, gravity, and thermodynamics at once.

**⚠️ Entropy scales with AREA, not volume** — a violation of everything ordinary
thermodynamic intuition suggests, and the origin of the **holographic principle**: the
degrees of freedom in a region are bounded by its boundary area in Planck units.

**Hawking radiation**: `T_H ∝ 1/M`. ⚠️ **Black holes have negative heat capacity — they get
hotter as they evaporate.** A solar-mass black hole has `T_H ≈ 60 nK`, far below the CMB,
so it absorbs more than it emits. **Evaporation time `∝ M³`** — ~10⁶⁷ years for a solar
mass.

**⚠️ The information paradox**: Hawking's original calculation gives exactly thermal
radiation, which is information-free. If the black hole evaporates completely, the
information in what fell in is destroyed — **and that is non-unitary, contradicting QM.**
Recent progress (**replica wormholes and the Page curve**, ~2019–20) suggests unitarity is
preserved, but ⚠️ **the mechanism of information return is not settled** (§17 → `physics-reference`).

---
