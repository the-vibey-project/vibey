---
id: skill-3-quantum-field-theory-dbc5ffc09a
purpose: 3 quantum field theory
source: src/vibey_tools/skills/plugins/fundamental-physics/skills/physics-quantum-mechanics-and-field-theory/SKILL.md
requires: ["skill-2-solved-systems-and-structure-1c9821f41d"]
links: []
---

## §3. Quantum Field Theory

### 3.1 The framework

**[DURABLE] Why fields:** combining QM with special relativity forces it. Relativity
permits particle creation and destruction (`E = mc²`), so **a fixed-particle-number Hilbert
space is untenable.** Fields are the objects; particles are their quantized excitations.

**Construction**: promote the field `φ(x)` to an operator, expand in modes, and the
coefficients become creation and annihilation operators — ⚠️ **the harmonic oscillator's
ladder operators, one per mode.** A "particle" is a quantum of excitation.

**The Lagrangian formulation** is the working language:
```
Klein–Gordon (spin 0):  ℒ = ½(∂_μφ)(∂^μφ) − ½m²φ²
Dirac (spin ½):         ℒ = ψ̄(iγ^μ∂_μ − m)ψ
Maxwell (spin 1):       ℒ = −¼F_μν F^μν
```

**⚠️ Gauge symmetry is the generative principle, and this is the deepest structural fact
in particle physics.** Take the free Dirac Lagrangian, demand invariance under a *local*
phase rotation `ψ → e^(iα(x))ψ`. The derivative spoils it. **To restore invariance you
must introduce a vector field `A_μ` transforming compensatingly, and replace `∂_μ` with
`D_μ = ∂_μ − iqA_μ`.** Out falls electromagnetism — the photon's existence, masslessness,
and coupling — **from a symmetry demand alone.**

**Generalize the group and you get the rest**: `U(1)` → QED. `SU(2)` → weak. `SU(3)` →
QCD, with **eight gluons** carrying colour charge themselves (⚠️ **because SU(3) is
non-abelian, gluons self-interact — which is why QCD confines and QED doesn't**).

**Path integral**: `⟨f|i⟩ = ∫𝒟φ e^(iS[φ]/ħ)` — sum over all field histories weighted by
`e^(iS/ħ)`. ⚠️ **The classical path emerges as the stationary-phase point**, which is the
cleanest statement of how classical mechanics sits inside quantum mechanics.

### 3.2 Renormalization

**[DURABLE] The conceptual shift that made QFT respectable.** Loop integrals diverge.
The historical response was to absorb infinities into redefined ("bare") parameters —
which worked and felt like a swindle.

**⚠️ Wilson's reframing (1970s) is the correct one and it changed the meaning entirely**:
a QFT is an **effective theory valid below some cutoff Λ**. Integrating out high-energy
modes makes couplings **run** with scale:
```
μ dg/dμ = β(g)
```
- **QED**: β > 0. ⚠️ **Coupling grows at high energy** — α goes from 1/137 at low energy to
  ~1/128 at the Z mass.
- **QCD**: β < 0. ⚠️ **Asymptotic freedom** (Gross, Politzer, Wilczek — Nobel 2004):
  quarks are nearly free at short distance and **confined at long distance**, which is why
  you never see an isolated quark.

**⚠️ "Renormalizable" stopped being a fundamental requirement and became a statement about
which terms dominate at low energy.** Non-renormalizable terms are suppressed by powers of
`E/Λ` — **which is why the Standard Model works so well without knowing what's above it,
and why the Fermi theory of beta decay was a perfectly good theory until it wasn't.**

### 3.3 Predictive success

**⚠️ QED's prediction of the electron anomalous magnetic moment agrees with experiment to
about twelve significant figures** — the most precisely verified prediction in science.
That number is the reason the framework is taken seriously despite §12 → `physics-measurement-problem-and-quantum-gravity`.

### 3.4 The Standard Model

**Gauge group `SU(3)_C × SU(2)_L × U(1)_Y`**, spontaneously broken to
`SU(3)_C × U(1)_EM`.

**Matter — three generations of fermions:**
```
Quarks   (u,d)  (c,s)  (t,b)        colour triplets, fractional charge
Leptons  (e,ν_e) (μ,ν_μ) (τ,ν_τ)     colourless
```
**Forces:** photon (EM), **W±, Z⁰** (weak, massive), **8 gluons** (strong).
**Higgs** — one scalar, found 2012 at ~125 GeV.

**⚠️ The Higgs mechanism, stated precisely, because the popular version is wrong.** A
scalar field with potential `V(φ) = μ²|φ|² + λ|φ|⁴` and `μ² < 0` has a **Mexican-hat**
shape; the vacuum sits at `|φ| = v/√2 ≈ 174 GeV`, breaking the symmetry **spontaneously**
(the Lagrangian keeps the symmetry; the ground state doesn't). **Gauge bosons acquire mass
by absorbing the would-be Goldstone modes** — the W and Z eat three, gaining longitudinal
polarizations. **Fermions get mass through separate Yukawa couplings `y_f`, and those
couplings are free parameters, not predictions.**

**⚠️ "The Higgs gives everything mass" is wrong.** It gives the W, Z, and fundamental
fermions their masses. **Over 98% of the mass of ordinary matter is QCD binding energy** —
the proton's ~938 MeV against its quarks' ~9 MeV of Higgs-derived mass.

**⚠️ 19+ free parameters** (masses, mixing angles, couplings, θ_QCD), plus more for neutrino
masses. **The Standard Model does not explain: why three generations, why these masses
(spanning 12 orders of magnitude), or why the gauge group is what it is.**

**Chirality**: ⚠️ **the weak force couples only to left-handed fermions**, which is the
sharpest parity violation in nature and remains structurally unexplained.
**CKM matrix** mixes quark generations and contains **one CP-violating phase** — ⚠️ **far
too little to explain the matter–antimatter asymmetry** (§17 → `physics-reference`).
