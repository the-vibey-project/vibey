---
id: skill-8-oscillations-and-resonance-53bb0796b4
purpose: 8 oscillations and resonance
source: src/vibey_tools/skills/plugins/newtonian-mechanics/skills/mech-rotation-rigid-bodies-and-oscillations/SKILL.md
requires: ["skill-7-rigid-bodies-and-gyroscopes-b99c2bd943"]
links: []
---

## §8. Oscillations and Resonance

**Simple harmonic motion** — ⚠️ **arises whenever the restoring force is proportional to
displacement, which is the leading-order behaviour of *any* smooth potential minimum.**
**That's why SHM is everywhere: it's the first term in a Taylor expansion.**
```
mẍ + kx = 0     →     x = A cos(ωt + φ),  ω = √(k/m)
Pendulum (small angle): ω = √(g/L)   ⚠️ small angle only — sin θ ≈ θ
                        ⚠️ period independent of amplitude ONLY in that approximation
```
**Damped**: `mẍ + bẋ + kx = 0` → **underdamped** (oscillates, decaying),
**critically damped** (⚠️ **fastest return to equilibrium without overshoot — what you
want for a door closer or a control system**), **overdamped** (slow, no overshoot).

**Driven and resonance**: amplitude peaks near `ω_drive ≈ ω₀`.
**Q factor** ≈ `ω₀/Δω` — ⚠️ **high Q means sharp resonance and slow decay.**
> **⚠️ GOTCHA — resonance is not automatically destructive, and the Tacoma Narrows bridge
> is not an example of it.** ⚠️ **That collapse is now attributed to aeroelastic flutter —
> a self-excited oscillation where the structure's motion changes the aerodynamic forces,
> a feedback instability rather than an external periodic driver matching a natural
> frequency.** **It's in every textbook as "resonance" and the attribution is wrong.**
