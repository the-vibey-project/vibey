---
id: skill-5-dynamics-the-balances-61b91f6ba7
purpose: 5 dynamics the balances
source: src/vibey_tools/skills/plugins/weather-science/skills/weather-dynamics-circulation-and-synoptic/SKILL.md
requires: []
links: ["skill-6-general-circulation-fd2200e57a"]
---

## §5. Dynamics — The Balances

**The forces on an air parcel**: pressure gradient force (⚠️ **from high to low, and it's
the only force that initiates motion**), **Coriolis** (⚠️ **apparent, from the rotating
frame — see a Newtonian-mechanics reference §10; it deflects right in the NH, left in the
SH, acts only on moving air, and is zero at the equator**), friction, and gravity.

### 5.1 Geostrophic balance
**⚠️ For large-scale flow away from the surface, the pressure gradient force and Coriolis
force balance almost exactly:**
```
f v_g = (1/ρ) ∂P/∂x        f = 2Ω sin φ    (the Coriolis parameter)
```
> **⚠️ GOTCHA — this means the wind blows ALONG the isobars, not across them.** **Low
> pressure on your left in the northern hemisphere (Buys Ballot's law).** ⚠️ **This is
> deeply counterintuitive and it is the single most important structural fact about
> mid-latitude weather.** **Air does not flow from high to low; it circles.**
>
> ⚠️ **Near the surface, friction breaks the balance** — wind backs across the isobars
> toward low pressure, **which is what produces convergence into lows and divergence out
> of highs**, and therefore ascent and cloud in lows.

**Gradient wind** adds curvature. **⚠️ Geostrophy fails near the equator** (`f → 0`),
which is why tropical meteorology is genuinely different.

### 5.2 Thermal wind
**⚠️ The vertical shear of the geostrophic wind is proportional to the horizontal
temperature gradient.**
**Consequence**: ⚠️ **the strong pole-to-equator temperature gradient in mid-latitudes
requires westerly winds increasing with height — which IS the jet stream.** **The jet is
not a separate phenomenon; it's a direct consequence of the temperature gradient.**

### 5.3 Vorticity
**Relative vorticity `ζ`** (spin relative to Earth) **+ planetary vorticity `f`** =
**absolute vorticity**. **Potential vorticity (PV)** — ⚠️ **conserved following the flow
under adiabatic, frictionless conditions, and it is the master variable of modern
dynamical meteorology.** **PV thinking lets you diagnose development from a single field.**

**⚠️ The vorticity view of weather**: air columns stretching gain vorticity, shrinking lose
it. **Upper-level divergence ahead of a trough drives surface convergence and ascent —
this is the mechanism of cyclogenesis** (§7.2).

---
