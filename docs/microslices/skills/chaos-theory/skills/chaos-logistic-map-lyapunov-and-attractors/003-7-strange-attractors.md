---
id: skill-7-strange-attractors-4af5da0741
purpose: 7 strange attractors
source: src/vibey_tools/skills/plugins/chaos-theory/skills/chaos-logistic-map-lyapunov-and-attractors/SKILL.md
requires: ["skill-6-lyapunov-exponents-adba4fd18f"]
links: ["skill-8-routes-to-chaos-d4c54ac808"]
---

## §7. Strange Attractors

**Lorenz (1963)** — derived from a drastically truncated model of thermal convection:
```
ẋ = σ(y − x)        ẏ = x(ρ − z) − y        ż = xy − βz
σ = 10, ρ = 28, β = 8/3    ⚠️ the classic parameters
```
**⚠️ Two lobes, never repeating, never crossing.** The trajectory orbits one wing, switches
to the other unpredictably. **Fractal dimension ≈ 2.06** — ⚠️ **more than a surface, less
than a volume, which is what "strange" means geometrically.**
**⚠️ Lorenz found it by accident**: he restarted a simulation from printed output rounded
to three decimals instead of the stored six, and the run diverged completely. **The
practical lesson arrived before the theory.**

**Rössler** — simpler, single-scroll, designed to be the minimal example.
**Hénon map** — a 2D map, `x_{n+1} = 1 − ax_n² + y_n`, `y_{n+1} = bx_n`; ⚠️ **zoom in and
the Cantor-set cross-section is directly visible.**
**Also**: the double pendulum, Duffing and van der Pol oscillators, Chua's circuit
(⚠️ **chaos you can build on a breadboard**), the standard map (§11 → `chaos-fractals-poincare-and-hamiltonian-chaos`).

**⚠️ A strange attractor is strange geometrically (fractal) and chaotic dynamically
(λ > 0), and these are logically independent** — **strange nonchaotic attractors exist.**
**Most people use "strange" to mean both; be aware they're different claims.**

---
