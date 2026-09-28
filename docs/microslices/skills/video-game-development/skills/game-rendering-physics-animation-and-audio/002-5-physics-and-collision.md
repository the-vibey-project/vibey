---
id: skill-5-physics-and-collision-feecf85642
purpose: 5 physics and collision
source: src/vibey_tools/skills/plugins/video-game-development/skills/game-rendering-physics-animation-and-audio/SKILL.md
requires: ["skill-4-rendering-c027ccd260"]
links: ["skill-6-animation-e0bfe0c01b"]
---

## §5. Physics and Collision

### 5.1 Use a physics engine

**Havok**, **PhysX**, **Jolt**, **Box2D**, **Bullet**, **Rapier**. **[VERSIONED] Jolt
became Godot 4.6's default physics engine (January 2026)**, closing much of Godot's
previous gap against Unity and Unreal on 3D physics fidelity — a good example of how
quickly this layer moves.

**[DURABLE] Most games do not want realistic physics.** They want *controllable* physics
that feels good. Character controllers are usually **kinematic** (you move them; you
resolve collisions manually) rather than dynamic rigid bodies, because rigid-body player
characters feel floaty, get stuck, and are hard to tune. This surprises people every time.

### 5.2 Collision detection

**Broad phase** (which pairs *might* collide — spatial hash, BVH, sweep-and-prune, grid,
octree) then **narrow phase** (do they actually — SAT, GJK/EPA, sphere/AABB/capsule tests).
**[DURABLE] The broad phase is where the algorithmic win is**; narrow-phase
micro-optimization matters far less than not testing 10,000 irrelevant pairs.

**Continuous collision detection (CCD)** for fast objects, or your bullets pass through
walls. **Sub-stepping** for stability. Layers and masks so things only collide with what
they should.

> **⚠️ GOTCHA — the classic physics bugs, all of which you will hit:** tunneling (fast
> object, thin wall — needs CCD or raycast movement); jitter (conflicting constraints, or
> a too-large timestep); objects gaining energy (integration error — use a semi-implicit
> Euler or better); the "sticky wall" (missing collision-margin handling); and framerate
> dependence (§2.1 → `game-engines-loop-and-architecture` — physics must be on a fixed timestep).

---
