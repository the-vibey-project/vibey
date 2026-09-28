---
id: skill-1-the-rocket-equation-f7a680a92e
purpose: 1 the rocket equation
source: src/vibey_tools/skills/plugins/rocket-science/skills/rocket-equation-nozzles-and-combustion/SKILL.md
requires: ["skill-0-routing-4856aa310d"]
links: ["skill-2-nozzle-thermodynamics-2d5121858c"]
---

## §1. The Rocket Equation

### 1.1 Derivation

**[DURABLE]** Take a vehicle of mass `m` moving at `v`. In time `dt` it expels `dm_p` of
propellant at exhaust velocity `v_e` relative to the vehicle. Momentum conservation in the
instantaneous rest frame:

```
m dv = −v_e dm          (dm negative: vehicle loses mass)
dv = −v_e (dm/m)
```
Integrate from `m₀` to `m_f`:

```
Δv = v_e · ln(m₀/m_f) = Isp · g₀ · ln(m₀/m_f)
```

**⚠️ Note what the derivation assumes**: no gravity, no drag, no back-pressure, constant
`v_e`, and thrust aligned with velocity. **Every one of those is violated in flight** —
which is what §8 → `rocket-orbital-mechanics-and-ascent`'s loss terms account for.

### 1.2 The consequences

Rearranged, the **mass ratio** `MR = m₀/m_f = exp(Δv / (Isp·g₀))`.

```
Δv required        MR needed at Isp=350s   Propellant fraction
2.0 km/s                  1.79                  44%
4.0 km/s                  3.21                  69%
6.0 km/s                  5.75                  83%
9.4 km/s (LEO)           15.6                   94%   ⚠️
12.0 km/s                33.1                   97%
```

**⚠️ At 94% propellant fraction, structure + engines + payload share 6%.** A stage
structural coefficient `ε = m_struct/(m_struct + m_prop)` of 0.06–0.10 is typical for a
good aluminium stage. **If ε alone were 0.06 you'd have zero payload** — this is precisely
why single-stage-to-orbit is marginal (§16.1 → `rocket-reference`).

### 1.3 Staging mathematics

For `n` stages with individual mass ratios, **Δv is additive**:
```
Δv_total = Σ Isp_i · g₀ · ln(MR_i)
```

**[DURABLE] The optimization**: for stages with equal `Isp` and equal `ε`, the Δv-optimal
split is **equal Δv per stage**. With differing Isp and ε, you maximize via Lagrange
multipliers, giving the condition that the **payload-ratio derivative be equal across
stages**. The practical result:

**⚠️ Optimal staging puts *more* Δv on the stage with the higher Isp and lower ε** —
which is why upper stages use hydrogen and are pushed to do a disproportionate share.

**Worked example — two-stage to 9.4 km/s:**
```
Stage 1: Isp 300 s (SL-optimized kerolox), ε = 0.06
Stage 2: Isp 450 s (hydrolox vacuum),      ε = 0.10

Split Δv 4.2 / 5.2 km/s:
  MR₁ = exp(4200/(300·9.807)) = 4.16
  MR₂ = exp(5200/(450·9.807)) = 3.26

Payload fraction ≈ Π [ (1/MR_i − ε_i) / (1 − ε_i) ]
  Stage 1: (0.240 − 0.06)/(0.94) = 0.192
  Stage 2: (0.307 − 0.10)/(0.90) = 0.230
  → λ ≈ 0.192 × 0.230 ≈ 4.4%
```
⚠️ **Note how sensitive this is**: if ε₂ rises from 0.10 to 0.15, stage-2 payload ratio
drops to 0.185 and total λ falls to 3.5% — **a 20% payload loss from a 5-point structural
coefficient change.** This is why mass growth kills programmes.

**⚠️ Diminishing returns**: going from 2 to 3 stages typically buys ~10–15% payload; 3 to 4
buys a few percent, at the cost of another separation event (a top failure mode, §13.4 → `rocket-aerodynamics-structures-guidance-and-reentry`).

### 1.4 Rate form and thrust
```
F = ṁ · v_e + (p_e − p_a)·A_e          [thrust with pressure term]
Isp = F / (ṁ · g₀)
```
**⚠️ The pressure term is why Isp is altitude-dependent** and why the same engine quotes two
numbers. Merlin 1D: ~282 s sea level, ~311 s vacuum. RL10: ~465 s, vacuum only.

---
