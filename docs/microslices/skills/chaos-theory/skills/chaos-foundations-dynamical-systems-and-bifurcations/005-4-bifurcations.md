---
id: skill-4-bifurcations-a0af6760ea
purpose: 4 bifurcations
source: src/vibey_tools/skills/plugins/chaos-theory/skills/chaos-foundations-dynamical-systems-and-bifurcations/SKILL.md
requires: ["skill-3-stability-and-linearization-6e637cca70"]
links: []
---

## §4. Bifurcations

**⚠️ A qualitative change in dynamics as a parameter varies.** The local ones:
```
Saddle-node (fold)   ⚠️ two fixed points collide and ANNIHILATE — the generic way
                     equilibria appear and disappear. Basis of TIPPING POINTS
Transcritical        two fixed points exchange stability
Pitchfork            ⚠️ symmetry breaking: one → three (supercritical) 
                     ⚠️ SUBCRITICAL pitchfork/saddle-node → HYSTERESIS and sudden jumps
Hopf                 ⚠️ fixed point → LIMIT CYCLE. Oscillation is born
Period-doubling      ⚠️ (maps) period-n → period-2n. THE route in §5
```
**⚠️ Supercritical vs subcritical is the practically important distinction**: supercritical
is continuous and reversible; ⚠️ **subcritical is sudden, involves hysteresis, and the
system does not return when you reverse the parameter.** **Every "tipping point" argument
is a subcritical bifurcation claim, whether or not it's stated that way.**

**Global bifurcations**: homoclinic and heteroclinic, **saddle-node on an invariant
circle (SNIC)**, ⚠️ **and crises — where an attractor suddenly changes size or is
destroyed by collision with an unstable orbit.**
