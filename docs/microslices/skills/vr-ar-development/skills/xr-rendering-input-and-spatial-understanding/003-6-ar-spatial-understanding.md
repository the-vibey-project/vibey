---
id: skill-6-ar-spatial-understanding-94f6c56e47
purpose: 6 ar spatial understanding
source: src/vibey_tools/skills/plugins/vr-ar-development/skills/xr-rendering-input-and-spatial-understanding/SKILL.md
requires: ["skill-5-input-and-interaction-17085c4c8b"]
links: []
---

## §6. AR Spatial Understanding

**Anchors** — ⚠️ **a pose the system continuously refines as its map improves.** **Attach
content to an anchor rather than to world coordinates**, because ⚠️ **the world origin
drifts as SLAM refines; anchored content stays put relative to the real world and
unanchored content visibly slides.**

**Plane detection** (horizontal/vertical), **mesh reconstruction** (⚠️ **scene meshing
gives you physics and occlusion geometry**), **semantic scene understanding** (this is a
wall / a table / a floor), **image and object tracking**, and **hit testing** against
detected geometry.

**⚠️ Occlusion is the hardest and most important AR correctness problem.** Without it,
virtual objects float in front of everything and the illusion never forms. **Approaches**:
depth from a sensor or stereo, reconstructed mesh, and **learned monocular depth** —
⚠️ **and note §2 → `xr-perceptual-constraints-displays-and-tracking`: on optical see-through hardware, true occlusion of the real world is
physically impossible because you can only add light.**

**Lighting estimation** — match virtual lighting to the real environment (ambient
intensity, colour temperature, dominant direction, environment probe). ⚠️ **A correctly
lit and shadowed object at the wrong scale still looks wrong; a mediocre model with a
correct contact shadow looks glued down. Contact shadows are the highest-leverage AR
rendering feature.**

**⚠️ Persistence and sharing**: cloud anchors and shared coordinate frames for multi-user
AR, and **localization against a saved map.** ⚠️ **Relocalization is fragile under changed
lighting and rearranged furniture** — design for it failing.
