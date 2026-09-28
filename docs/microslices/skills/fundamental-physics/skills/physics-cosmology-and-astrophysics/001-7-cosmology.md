---
id: skill-7-cosmology-27bba8be7e
purpose: 7 cosmology
source: src/vibey_tools/skills/plugins/fundamental-physics/skills/physics-cosmology-and-astrophysics/SKILL.md
requires: []
links: ["skill-8-stellar-astrophysics-adbed39b83"]
---

## §7. Cosmology

### 7.1 FLRW and the Friedmann equations

**Assume homogeneity and isotropy** (the cosmological principle) and the metric is forced:
```
ds² = −c²dt² + a(t)²[dr²/(1−kr²) + r²dΩ²]
```
Substituting into the field equations gives:
```
(ȧ/a)² = (8πG/3)ρ − kc²/a² + Λc²/3           Friedmann I
ä/a = −(4πG/3)(ρ + 3p/c²) + Λc²/3            Friedmann II
ρ̇ + 3(ȧ/a)(ρ + p/c²) = 0                     continuity
```
⚠️ **Note the `ρ + 3p` in the acceleration equation — pressure gravitates.** This is why
`w = p/ρc² < −1/3` (dark energy) produces acceleration and ordinary matter doesn't.

**Scaling with `a`**: matter `ρ ∝ a⁻³`, radiation `ρ ∝ a⁻⁴` (⚠️ **the extra factor from
redshifting**), curvature `∝ a⁻²`, **Λ constant**. **Hence the eras: radiation → matter →
Λ**, and the ordering is a consequence of the exponents, not a coincidence.

**⚠️ Redshift is not Doppler.** `1 + z = a(t_0)/a(t_e)` — wavelengths stretch with space
itself. **Recession velocities can and do exceed `c` without violating relativity**,
because nothing is moving *through* space faster than light.

### 7.2 ΛCDM

**Six parameters** fit essentially all cosmological data: `Ω_b h², Ω_c h², θ_*, τ, A_s, n_s`.
Derived: **≈ 5% baryons, ≈ 27% cold dark matter, ≈ 68% dark energy**, spatially flat to
sub-percent, age **13.8 Gyr**.

**The evidence pillars**: **CMB** (⚠️ **acoustic peaks whose positions and heights encode
the whole parameter set — the most information-dense dataset in cosmology**), **BBN**
(primordial D, ³He, ⁴He, ⁷Li abundances from the first three minutes — **a completely
independent measure of baryon density that agrees**), **large-scale structure and BAO**,
and **Type Ia supernovae** (the 1998 acceleration discovery).

### 7.3 Inflation

**⚠️ Motivated by three problems**: **horizon** (why is the CMB uniform across regions that
were never causally connected?), **flatness** (why is Ω so close to 1, when that's an
unstable fixed point?), and **monopoles**.

**Mechanism**: a scalar field in slow roll gives `a ∝ e^(Ht)`, expanding by `≳ e^60`.
⚠️ **The genuine triumph is not solving those problems — it's that quantum fluctuations of
the inflaton, stretched to cosmic scales, predict a nearly scale-invariant spectrum of
density perturbations with `n_s` slightly below 1.** **Planck measures `n_s ≈ 0.965`** —
a prediction made before the measurement.

⚠️ **What's not settled**: which inflaton, whether eternal inflation follows (and whether
that's science), and **primordial gravitational waves (`r`) remain undetected**, which
would be the decisive confirmation.

---
