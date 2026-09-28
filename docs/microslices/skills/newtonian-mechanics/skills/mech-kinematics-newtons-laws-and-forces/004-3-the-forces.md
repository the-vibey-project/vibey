---
id: skill-3-the-forces-d1f682ca43
purpose: 3 the forces
source: src/vibey_tools/skills/plugins/newtonian-mechanics/skills/mech-kinematics-newtons-laws-and-forces/SKILL.md
requires: ["skill-2-newton-s-laws-ea158a6436"]
links: []
---

## §3. The Forces

### 3.1 Gravity
`F = Gm₁m₂/r²`, and near a surface `W = mg`. ⚠️ **A spherically symmetric body attracts
external objects as if all its mass were at the centre** (Newton's shell theorem — and it
took him years, which is a useful thing to know when it's presented as obvious).
**⚠️ Inside a uniform shell, the field is exactly zero.**

**⚠️ Weight vs mass**: mass is invariant; weight is `mg` and depends on where you are.
**"Weightlessness" in orbit is free fall, not absence of gravity** — ⚠️ **gravity at ISS
altitude is about 90% of its surface value.** The station and its occupants are
accelerating together.

### 3.2 Normal force
**⚠️ Perpendicular to the surface, and it is not equal to `mg` in general.** It is
whatever it needs to be to prevent interpenetration — **on an incline, in an accelerating
lift, or under an applied force, it differs.** ⚠️ **"N = mg" is a special case that
students promote to a law.**

### 3.3 Friction
```
Static:  f_s ≤ μ_s N     ⚠️ an INEQUALITY — it takes whatever value prevents sliding,
                         up to the maximum
Kinetic: f_k = μ_k N     ⚠️ roughly constant, opposing relative motion; μ_k < μ_s
```
**⚠️ The inequality is the part people miss.** A block at rest on a table with no applied
force has **zero** friction, not `μ_s N`. **You compute static friction from equilibrium,
not from the formula** — the formula only gives you the threshold.

**⚠️ The Coulomb model's surprising claim**: friction is **independent of contact area**,
because real contact happens at asperities whose true contact area scales with normal
force. ⚠️ **It's an approximation — it fails for very soft materials, very clean surfaces
(which can cold-weld), and at high speed.** **Racing tyres are wide for thermal and wear
reasons the simple model doesn't capture.**

**Rolling resistance** is a different mechanism entirely — hysteretic deformation loss, not
sliding — and is much smaller.

### 3.4 Drag
```
Low Reynolds number (viscous):   F = −bv        ⚠️ linear
High Reynolds number (inertial): F = ½ρCdAv²    ⚠️ quadratic — the everyday case
```
**⚠️ Terminal velocity** when drag balances weight: `v_t = √(2mg/ρC_dA)`.
**⚠️ Quadratic drag makes the equations non-integrable in closed form** for most cases —
which is precisely why projectile problems in textbooks ignore it and why real ballistics
is numerical.

### 3.5 Spring and tension
**Hooke's law** `F = −kx` — ⚠️ **linear only within the elastic limit, and the minus sign
is the physics: the force opposes displacement, which is what makes oscillation
possible.**
**Tension** — ⚠️ **uniform throughout an ideal massless string, and an ideal pulley
changes tension's *direction* without changing its magnitude.** Real ropes have mass and
real pulleys have inertia and friction.
