---
id: skill-2-newton-s-laws-ea158a6436
purpose: 2 newton s laws
source: src/vibey_tools/skills/plugins/newtonian-mechanics/skills/mech-kinematics-newtons-laws-and-forces/SKILL.md
requires: ["skill-1-kinematics-5c770f960e"]
links: ["skill-3-the-forces-d1f682ca43"]
---

## §2. Newton's Laws

### 2.1 Stated precisely
**First law** — a body remains at rest or in uniform straight-line motion **unless acted on
by a net external force.**
> **⚠️ GOTCHA — the first law is not a special case of the second.** It looks redundant
> (`F=0 ⟹ a=0`), but its real content is **defining what an inertial frame is**: a frame in
> which the first law holds. ⚠️ **The second law is only valid in such frames**, so the
> first law is the precondition for the second, not a corollary of it (§10 → `mech-orbits-frames-analytical-mechanics-and-simulation`).

**Second law** — ⚠️ **properly `F = dp/dt`, not `F = ma`.** They agree only when mass is
constant. **For variable-mass systems — a rocket, a falling chain, a conveyor being
loaded — you must go back to momentum**, and ⚠️ **naively writing `F = ma` with `m(t)` is
wrong, because it ignores the momentum carried by the mass entering or leaving.** (See a
rocket-science reference for the correct derivation.)

**Third law** — forces come in equal, opposite pairs **on different bodies.**

### 2.2 ⚠️ The misconceptions the laws generate
**These are documented, robust, and survive instruction** — the Force Concept Inventory
literature exists because of them.
- **⚠️ "Motion requires a force."** The most persistent error in physics. **Constant
  velocity requires zero net force.** ⚠️ **It feels wrong because on Earth friction is
  always present, so maintaining motion does require force — to cancel friction, not to
  sustain the motion.**
- **⚠️ "A thrown ball has a forward force on it."** It does not. **After release, the only
  forces are gravity and drag.** The "force of the throw" is not a thing that persists —
  ⚠️ **what persists is momentum, and confusing the two is the whole error.**
- **⚠️ "The third-law pair cancels."** ⚠️ **They act on different bodies and therefore
  never cancel each other in a single body's free-body diagram.** **Cancellation would
  make all acceleration impossible.**
- **⚠️ "A heavier object falls faster."** Not in vacuum. In air, terminal velocity depends
  on the mass-to-drag ratio, so **heavier usually does fall faster in practice** — which
  is exactly why the misconception is so durable.
- **⚠️ "Centrifugal force pushes you outward."** ⚠️ **In an inertial frame there is no such
  force**; you feel the seat pushing you *inward* (centripetal) and your inertia resisting.
  **Centrifugal force is real and useful — but only in the rotating frame** (§10 → `mech-orbits-frames-analytical-mechanics-and-simulation`).

### 2.3 Free-body diagrams
**⚠️ The single most valuable procedural skill in mechanics, and it's mechanical:**
```
1. Isolate ONE body. Draw it alone.
2. Draw ONLY forces acting ON it. ⚠️ Not forces it exerts. Not "the force of motion."
3. Every force must have an identifiable other object exerting it.
   ⚠️ If you can't name the exerter, the force isn't real.
4. Choose axes — align one with the acceleration if possible.
5. Write ΣF = ma per axis. Solve.
```
**⚠️ Rule 3 eliminates nearly every spurious force students invent.**

---
