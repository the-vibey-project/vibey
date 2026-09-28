---
id: skill-5-the-logistic-map-3e6cb4c1a5
purpose: 5 the logistic map
source: src/vibey_tools/skills/plugins/chaos-theory/skills/chaos-logistic-map-lyapunov-and-attractors/SKILL.md
requires: []
links: ["skill-6-lyapunov-exponents-adba4fd18f"]
---

## §5. The Logistic Map

**⚠️ The most important toy model in mathematics**, and it earns the status:
```
x_{n+1} = r x_n (1 − x_n),     x ∈ [0,1],  r ∈ [0,4]
```
```
r < 1          → extinction (x → 0)
1 < r < 3      → stable fixed point at 1 − 1/r
r = 3          ⚠️ first period-doubling
r ≈ 3.449      period 4        r ≈ 3.544  period 8 ...
r∞ ≈ 3.5699    ⚠️ ACCUMULATION POINT — onset of chaos
r > r∞         chaos, ⚠️ interleaved with PERIODIC WINDOWS
r ≈ 3.828      ⚠️ the period-3 window (see Sharkovskii, below)
r = 4          fully chaotic, conjugate to the tent map
```

### 5.1 ⚠️ Feigenbaum universality — the deep result
**The period-doubling parameter intervals shrink at a constant ratio:**
```
δ = 4.669201609...    ⚠️ the ratio of successive parameter intervals
α = 2.502907875...    the scaling of the attractor's spatial structure
```
> **⚠️ GOTCHA — these constants are UNIVERSAL, and this is the genuinely astonishing part.**
> ⚠️ **Any one-dimensional map with a smooth quadratic maximum period-doubles with the
> same δ** — the logistic map, the sine map, a dripping tap, a driven oscillator, a
> convecting fluid. **The constants have been measured in physical experiments.**
> **Feigenbaum's insight (1978) was that this is a renormalization group phenomenon** —
> ⚠️ **the same mathematical machinery as universality in critical phase transitions.**
> **The microscopic details are irrelevant; only the order of the maximum matters.**

### 5.2 ⚠️ "Period three implies chaos"
**Li and Yorke (1975)** — for a continuous 1D map, **the existence of a period-3 orbit
implies orbits of every period, plus an uncountable set of aperiodic orbits.**
**⚠️ This is a special case of Sharkovskii's theorem (1964), which gives a complete
ordering of periods**: if a map has a periodic orbit of period `p`, it has orbits of every
period below `p` in the Sharkovskii ordering. **Period 3 sits at the top, so it implies
everything.** ⚠️ **And the paper's title gave the field its name.**

---
