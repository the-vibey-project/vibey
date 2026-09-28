---
id: skill-6-lyapunov-exponents-adba4fd18f
purpose: 6 lyapunov exponents
source: src/vibey_tools/skills/plugins/chaos-theory/skills/chaos-logistic-map-lyapunov-and-attractors/SKILL.md
requires: ["skill-5-the-logistic-map-3e6cb4c1a5"]
links: ["skill-7-strange-attractors-4af5da0741"]
---

## §6. Lyapunov Exponents

**⚠️ The quantitative measure of sensitivity.** For an infinitesimal separation `δ₀`:
```
|δ(t)| ≈ |δ₀| e^(λt)
```
**⚠️ An n-dimensional system has n Lyapunov exponents (the Lyapunov spectrum).**
```
λ_max > 0   ⚠️ CHAOS — this is the operational definition
λ_max = 0   marginal / quasi-periodic (⚠️ a flow always has one zero exponent along
            the trajectory direction)
λ_max < 0   converging to a fixed point
Σλᵢ < 0     ⚠️ dissipative — phase space volume contracts
Σλᵢ = 0     ⚠️ conservative/Hamiltonian (Liouville) — §11
```
**⚠️ The signature of a strange attractor in 3D is (+, 0, −) with the sum negative**:
stretching in one direction, neutral along the flow, strong contraction — **volume
shrinks onto a fractal set while trajectories on it separate.** **That's stretch-and-fold
expressed in exponents.**

**⚠️ The Lyapunov time `1/λ_max` is the practically useful number**: the timescale on which
errors grow by `e`.
> **⚠️ GOTCHA — the predictability horizon scales LOGARITHMICALLY with initial accuracy.**
> ```
> t_horizon ≈ (1/λ) ln(tolerance/δ₀)
> ```
> ⚠️ **Improving your measurements by a factor of 1000 buys you only `ln(1000)/λ ≈ 6.9/λ`
> of extra prediction time.** **A few more Lyapunov times, not a thousand times longer.**
> **This is why better instruments cannot rescue long-range weather forecasting**, and it
> is the single most practically important consequence of chaos.

---
