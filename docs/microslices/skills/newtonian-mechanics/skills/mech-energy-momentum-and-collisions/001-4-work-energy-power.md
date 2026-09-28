---
id: skill-4-work-energy-power-15d7336605
purpose: 4 work energy power
source: src/vibey_tools/skills/plugins/newtonian-mechanics/skills/mech-energy-momentum-and-collisions/SKILL.md
requires: []
links: ["skill-5-momentum-and-collisions-1e3703ff6d"]
---

## §4. Work, Energy, Power

```
W = ∫F·dr           ⚠️ the dot product: only the component along displacement does work
KE = ½mv²           PE_grav = mgh (local) = −GMm/r (general)
PE_spring = ½kx²    P = dW/dt = F·v
```
**Work-energy theorem**: `W_net = ΔKE`. ⚠️ **Always true — it's just `F = ma` integrated
over displacement.**

**⚠️ Conservative forces** — work is path-independent, equivalently `∮F·dr = 0`,
equivalently `∇×F = 0`. **Only conservative forces admit a potential energy.** Gravity and
springs are conservative; **friction and drag are not**, which is why there's no "friction
potential energy."

**Mechanical energy conservation** `KE + PE = const` — ⚠️ **only when no non-conservative
force does work.** Otherwise `ΔKE + ΔPE = W_nc`.

> **⚠️ GOTCHA — "energy is lost to friction" is a shorthand that hides the physics.**
> ⚠️ **Energy is never lost.** It becomes thermal energy — disordered kinetic energy of
> molecules. **The distinction matters because it's the entry point to the second law**:
> the energy is still there, it's just no longer available to do work. **See a
> chemistry-foundations reference on entropy for why.**

### 4.5 ⚠️ Why conservation laws are deeper than Newton's laws
**Noether's theorem (1918)**: every continuous symmetry of the action yields a conserved
quantity.
```
Time-translation symmetry       →  energy conservation
Spatial-translation symmetry    →  momentum conservation
Rotational symmetry             →  angular momentum conservation
```
**⚠️ This is one of the most important results in physics** and it explains something
otherwise mysterious: **why conservation laws survive the transition to relativity and
quantum mechanics while `F = ma` does not.** ⚠️ **The conservation laws aren't consequences
of Newtonian dynamics — Newtonian dynamics is one realization of the underlying
symmetries.**

---
