---
id: skill-7-rigid-bodies-and-gyroscopes-b99c2bd943
purpose: 7 rigid bodies and gyroscopes
source: src/vibey_tools/skills/plugins/newtonian-mechanics/skills/mech-rotation-rigid-bodies-and-oscillations/SKILL.md
requires: ["skill-6-rotation-47790d8830"]
links: ["skill-8-oscillations-and-resonance-53bb0796b4"]
---

## §7. Rigid Bodies and Gyroscopes

**General rigid body motion = translation of the centre of mass + rotation about it.**
**⚠️ In 3D, `I` is a tensor, not a scalar**, and `L = Iω` means ⚠️ **`L` and `ω` are
generally not parallel.** **The principal axes are the eigenvectors of the inertia tensor**
— rotation about those is the only case where they align.

**⚠️ The intermediate axis theorem (Dzhanibekov effect)**: rotation about the axes of
largest and smallest moment of inertia is stable; **rotation about the intermediate axis
is unstable** and the object tumbles chaotically. ⚠️ **This is a real, dramatic, and
completely classical effect — throw a book or a tennis racket and watch it flip.**

**Gyroscopic precession**: `τ = dL/dt` means ⚠️ **a torque perpendicular to `L` changes its
*direction*, not its magnitude.** A spinning top under gravity precesses rather than
falling. ⚠️ **This is the most counterintuitive result in classical mechanics and it is
pure `τ = dL/dt`** — no new physics, just the vector nature of the equation taken
seriously. **Nutation** is the additional wobble.

**Static equilibrium** requires **both** `ΣF = 0` and `Στ = 0`. ⚠️ **Torque must be
computed about a chosen point — and it's zero about every point if it's zero about one,
provided `ΣF = 0`. Choosing the right pivot (one that kills an unknown force) is the whole
trick to statics problems.**

---
