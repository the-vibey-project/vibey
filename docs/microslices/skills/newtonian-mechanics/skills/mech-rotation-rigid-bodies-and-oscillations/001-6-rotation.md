---
id: skill-6-rotation-47790d8830
purpose: 6 rotation
source: src/vibey_tools/skills/plugins/newtonian-mechanics/skills/mech-rotation-rigid-bodies-and-oscillations/SKILL.md
requires: []
links: ["skill-7-rigid-bodies-and-gyroscopes-b99c2bd943"]
---

## §6. Rotation

```
τ = r × F              ⚠️ a cross product — magnitude rF sinθ, direction by right-hand rule
I = Σmᵢrᵢ²             moment of inertia — ⚠️ depends on the AXIS, not just the body
τ = Iα                 (fixed axis)
L = Iω  or  L = r × p
KE_rot = ½Iω²
```
**⚠️ Moment of inertia is not a property of an object alone** — it's a property of an
object *and an axis*. **The same rod has `mL²/12` about its centre and `mL²/3` about its
end.**

**Parallel axis theorem**: `I = I_cm + Md²`. ⚠️ **Which shows `I` is always minimized about
an axis through the centre of mass.**

**Common values** (§16 → `mech-reference`): hoop `MR²`, disc `½MR²`, solid sphere `⅖MR²`, shell `⅔MR²`.
**⚠️ The classic demonstration**: objects rolling down an incline race in order of `I/MR²`,
**independent of mass and radius** — a solid sphere always beats a disc, which always
beats a hoop.

**Rolling without slipping**: `v = ωR`, `a = αR`. ⚠️ **The contact point is instantaneously
at rest, which is why static friction acts and does no work** — this is why rolling can
conserve mechanical energy while sliding cannot.

**⚠️ Angular momentum conservation** when net external torque is zero. **The spinning
skater pulling arms in — and note that `KE = L²/2I` means KE *increases* as `I` decreases.
The skater does work pulling their arms in against the centrifugal effect.** ⚠️ **That
energy doesn't come from nowhere, and the question "where does it come from?" is the good
one.**

---
