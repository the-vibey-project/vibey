---
id: skill-23-compressible-flow-e6a1406c98
purpose: 23 compressible flow
source: src/vibey_tools/skills/plugins/thermodynamics-fluid-mechanics/skills/thermo-dimensional-analysis-flows-turbulence-and-turbomachinery/SKILL.md
requires: ["skill-22-turbulence-294ce32103"]
links: ["skill-24-turbomachinery-8afba2a973"]
---

## §23. Compressible Flow

```
⚠️ c = √(γRT)     Ma = V/c
STAGNATION PROPERTIES  T₀/T = 1 + ((γ−1)/2)Ma²
⚠️ ISENTROPIC NOZZLE  subsonic: area DOWN → velocity UP.
   ⚠️ SUPERSONIC: area UP → velocity UP. The reversal is why rocket and
   supersonic nozzles are converging-DIVERGING
⚠️ CHOKING        at the throat Ma = 1; mass flow becomes INDEPENDENT of
   downstream pressure. ⚠️ You cannot pull more through by lowering it
NORMAL SHOCK      ⚠️ discontinuous, irreversible, always supersonic→subsonic.
   ⚠️ Entropy INCREASES across it; stagnation pressure drops
OBLIQUE SHOCK / PRANDTL-MEYER EXPANSION  ⚠️ shocks compress abruptly;
   expansions are gradual and isentropic
FANNO (friction) and RAYLEIGH (heat addition) flow
```
**⚠️ Wave drag and the transonic regime**: ⚠️ **local supersonic pockets form on a wing
below Ma = 1, terminated by shocks — which is the drag rise, and the reason for swept
wings and supercritical aerofoils.**

---
