---
id: skill-8-stellar-astrophysics-adbed39b83
purpose: 8 stellar astrophysics
source: src/vibey_tools/skills/plugins/fundamental-physics/skills/physics-cosmology-and-astrophysics/SKILL.md
requires: ["skill-7-cosmology-27bba8be7e"]
links: ["skill-9-compact-objects-b7c7e679a3"]
---

## §8. Stellar Astrophysics

**[DURABLE] Stellar structure equations** — four coupled ODEs closed by an equation of
state and opacity:
```
dP/dr = −Gm(r)ρ/r²              hydrostatic equilibrium
dm/dr = 4πr²ρ                   mass continuity
dL/dr = 4πr²ρε                  energy generation
dT/dr = −3κρL/(16πacr²T³)       radiative transport (or the adiabatic gradient if convective)
```

**⚠️ The Eddington limit** — where radiation pressure balances gravity:
`L_Edd = 4πGMm_p c/σ_T ≈ 1.26×10³¹ (M/M_⊙) W`. **This caps stellar masses and accretion
rates**, and is why supermassive black hole growth has a timescale problem (§17 → `physics-reference`).

**Nuclear burning**: **pp chain** (dominant below ~1.3 M_⊙), **CNO cycle** (⚠️ **`∝ T¹⁵`
versus pp's `T⁴` — the extreme temperature sensitivity is why massive stars are convective
in the core and low-mass stars aren't**), **triple-alpha** (⚠️ **requires the Hoyle
resonance in ¹²C, predicted from the existence of carbon and then found**), and successive
burning to iron.

**⚠️ Iron is the endpoint because ⁵⁶Fe has the highest binding energy per nucleon.**
Fusion beyond it consumes energy rather than releasing it — which is why the core collapses.

**The mass-luminosity relation `L ∝ M^3.5`** has a brutal consequence:
⚠️ **lifetime `∝ M/L ∝ M^−2.5`.** The Sun lasts 10 Gyr; a 30 M_⊙ star lasts a few Myr.

---
