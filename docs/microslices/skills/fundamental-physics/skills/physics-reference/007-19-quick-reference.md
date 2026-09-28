---
id: skill-19-quick-reference-afa00c3f9a
purpose: 19 quick reference
source: src/vibey_tools/skills/plugins/fundamental-physics/skills/physics-reference/SKILL.md
requires: ["skill-18-textbooks-9a4b2edbef"]
links: ["skill-20-method-c7a2a16169"]
---

## §19. Quick Reference

### 19.1 The equations
```
iħ ∂|ψ⟩/∂t = Ĥ|ψ⟩                     Schrödinger
σ_A σ_B ≥ ½|⟨[Â,B̂]⟩|                  uncertainty
⟨f|i⟩ = ∫𝒟φ e^(iS/ħ)                  path integral
G_μν + Λg_μν = 8πG T_μν /c⁴           Einstein field equations
ds² = −(1−r_s/r)c²dt² + …             Schwarzschild
S_BH = k_B A/(4ℓ_P²)                  Bekenstein–Hawking
T_H = ħc³/(8πGMk_B)                   Hawking temperature
(ȧ/a)² = 8πGρ/3 − kc²/a² + Λc²/3      Friedmann
1 + z = a(t₀)/a(t_e)                  cosmological redshift
dP/dr = −Gmρ/r²                       hydrostatic equilibrium
L_Edd = 4πGMm_p c/σ_T                 Eddington limit
E² = (pc)² + (mc²)²                   relativistic energy
```

### 19.2 Scale ladder
```
Planck length        10⁻³⁵ m       ⚠️ where §12 bites
Proton               10⁻¹⁵ m
Atom                 10⁻¹⁰ m
Human                10⁰ m
Earth                10⁷ m
Sun                  10⁹ m
Solar system         10¹³ m
Light year           10¹⁶ m
Galaxy               10²¹ m
Observable universe  10²⁶ m        ⚠️ ~93 Gly across, larger than 13.8 Gly × 2 — expansion
```

### 19.3 Which framework applies
| Regime | Use |
|---|---|
| Small, slow | Quantum mechanics (§1 → `physics-quantum-mechanics-and-field-theory`) |
| Small, fast, particle number varying | QFT (§3 → `physics-quantum-mechanics-and-field-theory`) |
| Large, weak gravity | Newton |
| Large, strong gravity or precision timing | GR (§4.2 → `physics-relativity-black-holes-and-gravitational-waves`) |
| Large mass **and** small scale | ⚠️ **Nobody knows (§12 → `physics-measurement-problem-and-quantum-gravity`)** |
| Whole universe, large scale | FLRW + ΛCDM (§7 → `physics-cosmology-and-astrophysics`) |

---
