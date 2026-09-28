---
id: skill-3-working-fluid-properties-and-phase-behaviour-6b9f4504d6
purpose: 3 working fluid properties and phase behaviour
source: src/vibey_tools/skills/plugins/engines-generators-and-fuels/skills/engines-thermodynamics-and-the-carnot-ceiling/SKILL.md
requires: ["skill-2-the-carnot-efficiency-ceiling-419b437e89"]
links: ["skill-quick-reference-cd7759deb7"]
---

## §3 Working fluid properties and phase behaviour

The choice of working fluid determines what kind of engine you have: **water/steam** for Rankine
(§4–§6 → `engines-rankine-steam-engines-and-turbines`), **air** for Brayton and Otto (§7–§11 →
`engines-otto-diesel-brayton-stirling-and-combined-cycles`), **refrigerants** for heat pumps.
Critical properties follow.

### Saturation

At a given pressure a pure substance boils at **exactly one** temperature. While boiling, adding
heat changes the **QUALITY** (vapour fraction) but not the temperature.

This is why a steam boiler at a given pressure produces steam at a fixed temperature — and why
**raising the pressure raises the boiling point**, allowing higher-temperature steam and thus higher
Carnot efficiency (§2). Pressure is the knob; temperature is the consequence.

### Latent heat

The energy to change phase is **enormous** compared with sensible heat. Water's latent heat of
vaporization is roughly **540 times** the energy to raise one gram by 1°C.

This is why phase change dominates thermal engineering — an incredibly dense way to store and
transport energy.

### Critical point

Above the critical temperature and pressure there is **no distinction between liquid and vapour**.
Supercritical fluids have liquid-like density and gas-like transport properties.

Modern ultra-supercritical steam plants operate above water's critical point: **374°C, 22.1 MPa**.

### Ideal gas law

    Pv = RT

Good at **low pressure and high temperature relative to critical**. For liquids and solids use
tabulated properties or incompressible approximations.

> **Applying the ideal gas law near saturation is a classic and serious error.** If the state is
> anywhere near the saturation line, reach for steam tables or a property library — not `Pv = RT`.

### Specific heats and γ

- **c_p > c_v always**, because constant-pressure heating must also do expansion work.
- For ideal gases, **c_p − c_v = R**.
- The ratio **γ = c_p/c_v** appears in every gas-cycle efficiency formula and determines how
  temperature changes during compression and expansion.

γ is the parameter that carries §3 into the gas cycles: it is what turns a compression ratio into a
temperature ratio, and therefore into an efficiency (§7–§11 →
`engines-otto-diesel-brayton-stirling-and-combined-cycles`).
