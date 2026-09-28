---
id: skill-7-systems-biology-4bf74f83b0
purpose: 7 systems biology
source: src/vibey_tools/skills/plugins/biomedical-engineering-technical/skills/biomed-structural-systems-biology-and-pharmacology/SKILL.md
requires: ["skill-6-structural-biology-0fb8c24163"]
links: ["skill-8-pk-pd-4378cf5f70"]
---

## §7. Systems Biology

**Mass-action kinetics**: `d[X]/dt = Σ (production) − Σ (consumption)`.
**Michaelis–Menten**: `v = V_max[S]/(K_m + [S])` — ⚠️ **valid under the quasi-steady-state
assumption ([S] ≫ [E]), which is violated inside cells more often than people assume.**
**Hill equation**: `θ = [L]^n/(K_d + [L]^n)` — cooperativity, and `n` is the steepness of
the switch.

**Network motifs** that recur and what they do: **negative feedback** (homeostasis, noise
reduction), **positive feedback** (⚠️ **bistability — a switch**), **coherent feedforward
loop** (⚠️ **persistence detection: filters transient inputs**), **incoherent feedforward
loop** (pulse generation, fold-change detection), **oscillators** (negative feedback plus
delay — circadian clocks, p53).

**Flux balance analysis** for metabolism: `S·v = 0` at steady state, then maximize an
objective (usually growth) by linear programming subject to flux bounds. ⚠️ **No kinetic
parameters needed, which is why it scales to genome-scale models — and why it can't
predict dynamics.**

**Stochastic simulation** — **Gillespie's algorithm** for exact trajectories when molecule
counts are low. ⚠️ **Necessary because transcription factors can number in the tens per
cell, where the deterministic ODE is simply wrong.**

---
