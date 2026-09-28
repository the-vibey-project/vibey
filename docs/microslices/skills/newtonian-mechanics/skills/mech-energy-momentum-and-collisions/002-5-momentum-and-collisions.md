---
id: skill-5-momentum-and-collisions-1e3703ff6d
purpose: 5 momentum and collisions
source: src/vibey_tools/skills/plugins/newtonian-mechanics/skills/mech-energy-momentum-and-collisions/SKILL.md
requires: ["skill-4-work-energy-power-15d7336605"]
links: []
---

## §5. Momentum and Collisions

`p = mv`, and **impulse** `J = ∫F dt = Δp`.
**⚠️ Momentum is conserved for any isolated system, regardless of the internal forces** —
this follows directly from the third law, and it's more robust than energy conservation
because it doesn't care whether the interaction is dissipative.

**⚠️ The impulse insight that saves lives**: for a given `Δp`, **extending the collision
time reduces the peak force.** Crumple zones, airbags, helmets, and bending your knees on
landing are all this. **The momentum change is fixed by physics; the force is a design
choice.**

**Collisions**:
```
Elastic     ⚠️ KE conserved AND momentum conserved
Inelastic   momentum conserved, KE not
Perfectly inelastic  they stick; ⚠️ maximum KE loss consistent with momentum conservation
```
**⚠️ The 1D elastic collision result worth memorizing**: **equal masses exchange
velocities.** (Newton's cradle, and the basis of neutron moderation — ⚠️ **which is why
moderators use light nuclei: hydrogen has nearly the same mass as a neutron and takes the
most energy per collision.**)

**Centre of mass**: `R = Σmᵢrᵢ/Σmᵢ`. ⚠️ **The centre of mass moves as though all mass were
concentrated there and all external force applied there — regardless of how complicated
the internal motion is.** **An exploding shell's centre of mass continues on the original
parabola.**
