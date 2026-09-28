---
id: skill-4-ac-impedance-filters-09792fcdac
purpose: 4 ac impedance filters
source: src/vibey_tools/skills/plugins/electrical-engineering/skills/ee-fundamentals-components-and-circuit-analysis/SKILL.md
requires: ["skill-3-dc-analysis-580757f7af"]
links: []
---

## §4. AC, Impedance, Filters

**Impedance** is complex resistance:
```
Z_R = R          Z_L = jωL          Z_C = 1/(jωC)          ω = 2πf
|Z| = √(R² + X²)          θ = arctan(X/R)
```
⚠️ **Inductive reactance rises with frequency; capacitive reactance falls.** That single
fact explains filters, decoupling, and most parasitic behaviour.

**RC filters**:
```
f_c = 1/(2πRC)           ⚠️ −3 dB point, 20 dB/decade rolloff for first order
τ = RC                   63% of final value in one τ; ~99% in 5τ
```
**RL**: `τ = L/R`. **Resonance**: `f₀ = 1/(2π√(LC))`, with **Q** setting sharpness.

**Filter types**: low-pass, high-pass, band-pass, notch. **Topologies**: passive RC/LC,
active Sallen-Key (§6 → `ee-semiconductors-op-amps-logic-and-power`), **Butterworth** (⚠️ **maximally flat passband — the default
choice**), Chebyshev (steeper, with passband ripple), Bessel (⚠️ **linear phase — use it
when waveform shape matters**).

**dB**: `20·log₁₀(V₁/V₂)` for voltage, `10·log₁₀(P₁/P₂)` for power.
⚠️ **−3 dB is half power, not half voltage** (half voltage is −6 dB). **This trips people
constantly.**

**⚠️ For a software dev, the most useful AC insight**: **a digital edge is a broadband
signal**. Its spectrum extends to roughly `f_knee ≈ 0.35/t_rise`. **A 1 ns edge has
significant energy to ~350 MHz regardless of how slowly you're clocking it** — which is
why §9 → `ee-signal-integrity-emc-and-pcb-design` and §10 → `ee-signal-integrity-emc-and-pcb-design` apply to "slow" circuits.
