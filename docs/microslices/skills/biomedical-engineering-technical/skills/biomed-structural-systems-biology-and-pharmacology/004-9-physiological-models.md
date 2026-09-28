---
id: skill-9-physiological-models-4e282638ff
purpose: 9 physiological models
source: src/vibey_tools/skills/plugins/biomedical-engineering-technical/skills/biomed-structural-systems-biology-and-pharmacology/SKILL.md
requires: ["skill-8-pk-pd-4378cf5f70"]
links: []
---

## §9. Physiological Models

**⚠️ Hodgkin–Huxley (1952)** — still the foundation of computational neuroscience:
```
C_m dV/dt = I_ext − ḡ_Na m³h (V−E_Na) − ḡ_K n⁴ (V−E_K) − ḡ_L(V−E_L)
dx/dt = α_x(V)(1−x) − β_x(V)x        for x ∈ {m, h, n}
```
**⚠️ The gating variables are the insight**: `m³h` and `n⁴` — activation raised to a power
(multiple independent gates) times inactivation. **Four coupled nonlinear ODEs producing an
action potential from first principles.**

**Reduced models**: **FitzHugh–Nagumo** (2D, captures excitability and the phase-plane
geometry), **integrate-and-fire** and **Izhikevich** (⚠️ **computationally cheap enough for
large networks, and reproduces most observed spiking patterns with four parameters**).

**Nernst and GHK**:
```
E_ion = (RT/zF)·ln([ion]_out/[ion]_in)      ⚠️ ~61.5/z · log₁₀(ratio) mV at 37 °C
```

**Cardiac electrophysiology**: ionic models (Luo-Rudy, ten Tusscher, O'Hara-Rudy) coupled
by the **monodomain or bidomain** reaction-diffusion equation for tissue propagation.
⚠️ **Reentry and spiral waves are the mechanism of many arrhythmias, and they emerge from
the tissue equations, not the cell model.**

**Hemodynamics**: **Windkessel** — the 2-element model is `C dP/dt + P/R = Q(t)`, a
capacitor-resistor analogue of arterial compliance and peripheral resistance.
**Poiseuille**: `Q = πΔP r⁴/(8µL)` — ⚠️ **the `r⁴` is why a small stenosis has enormous
consequence; halving radius cuts flow 16-fold.**
**Reynolds number** `Re = ρvD/µ` — ⚠️ **blood flow is mostly laminar (Re < 2000); turbulence
appears at stenoses and valves and is what a bruit or murmur is.**
**⚠️ Blood is non-Newtonian** — shear-thinning, with the Fåhræus–Lindqvist effect reducing
apparent viscosity in small vessels.

**Respiratory**: compliance `C = ΔV/ΔP`, resistance, the **equation of motion**
`P = V/C + R·V̇ + PEEP`, and dead space via the Bohr equation.
