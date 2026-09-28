---
id: skill-6-animation-e0bfe0c01b
purpose: 6 animation
source: src/vibey_tools/skills/plugins/video-game-development/skills/game-rendering-physics-animation-and-audio/SKILL.md
requires: ["skill-5-physics-and-collision-feecf85642"]
links: ["skill-7-audio-e6fb999462"]
---

## §6. Animation

- **Skeletal animation**: bones, skinning (linear blend or dual-quaternion), the
  bind pose, and the eternal problem of the elbow that collapses.
- **Blend trees / blend spaces** — parameter-driven blending (speed, direction) is how
  locomotion actually works.
- **State machines and layers** — the standard authoring model; upper body and lower body
  on separate layers.
- **Root motion vs. in-place** — **[CONTESTED]** root motion looks better and fights your
  character controller; in-place is controllable and can foot-slide. Most action games use
  in-place with **foot IK**; most third-person cinematic games use root motion.
- **IK** — foot placement on slopes, look-at, hand placement on ledges. Two-bone IK covers
  most of it; FABRIK and CCD for chains.
- **Animation compression** matters enormously for memory in large games.
- **Procedural** — additive layers, ragdolls, physical animation blends, and increasingly
  ML-based motion matching (**Motion Matching** replaced hand-built state machines in a
  number of AAA locomotion systems).

**[DURABLE] Animation is where "game feel" (§12 → `game-performance-feel-and-shipping`) mostly lives.** Attack-cancel windows,
animation-driven hitboxes, blend-out times, and root-motion authority are gameplay design
decisions expressed as animation data — not art polish applied afterward.

---
