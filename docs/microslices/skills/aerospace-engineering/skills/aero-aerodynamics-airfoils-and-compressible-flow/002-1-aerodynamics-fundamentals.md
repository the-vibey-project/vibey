---
id: skill-1-aerodynamics-fundamentals-b5af570daf
purpose: 1 aerodynamics fundamentals
source: src/vibey_tools/skills/plugins/aerospace-engineering/skills/aero-aerodynamics-airfoils-and-compressible-flow/SKILL.md
requires: ["skill-0-routing-7c61a555c4"]
links: ["skill-2-airfoils-and-wings-6c92ffbfd7"]
---

## §1. Aerodynamics Fundamentals

### 1.1 The governing quantities
```
Dynamic pressure   q = ½ρV²      ⚠️ everything aerodynamic scales with this
Lift               L = ½ρV²S·C_L
Drag               D = ½ρV²S·C_D
Reynolds number    Re = ρVL/μ    ⚠️ inertial/viscous — sets laminar vs turbulent
Mach number        M = V/a       ⚠️ compressibility
```
**⚠️ `C_L` and `C_D` are non-dimensional and that's the point**: they let you transfer
wind-tunnel results to full-scale aircraft **provided Reynolds and Mach match** —
⚠️ **and matching both simultaneously at model scale is often impossible, which is the
central difficulty of experimental aerodynamics.**

### 1.2 ⚠️ How lift actually works
> **⚠️ GOTCHA — the "equal transit time" explanation is simply false, and it is what most
> people were taught.** ⚠️ **It claims air over the longer upper surface must travel faster
> to "meet up" with air below. There is no physical reason parcels must meet, and
> measurement shows upper-surface flow arrives *earlier*, not simultaneously.**
> **The explanation also fails to account for symmetric airfoils, flat plates, and
> inverted flight, all of which generate lift perfectly well.**

**⚠️ Two correct and complementary explanations:**
- **Newtonian / momentum**: ⚠️ **the wing deflects air downward; the reaction force is
  lift.** `L = ṁ·Δv` in essence. **Correct, intuitive, and doesn't tell you how much.**
- **Circulation / Kutta-Joukowski**: `L' = ρV∞Γ` — ⚠️ **lift per unit span equals density ×
  freestream velocity × circulation.** **The Kutta condition** (⚠️ **flow must leave the
  sharp trailing edge smoothly**) **determines `Γ` uniquely, which is what makes the
  theory predictive.** **This is the quantitative version.**

**⚠️ They are not competing explanations — they are the same physics in different
bookkeeping.** **Bernoulli is valid along a streamline and correctly relates the pressure
field to the velocity field; the error is in the false claim about *why* velocities
differ, not in Bernoulli itself.**

**Boundary layer**: ⚠️ **the thin region where viscosity matters and velocity goes from
zero at the wall to freestream.** **Laminar (low drag, easily separated) vs turbulent
(higher skin friction, ⚠️ far more resistant to separation — which is why turbulators and
vortex generators are deliberately added).**
**⚠️ Separation** occurs under an adverse pressure gradient; ⚠️ **it is the mechanism
behind stall, and it is a boundary-layer phenomenon, not a wing-shape phenomenon.**

---
