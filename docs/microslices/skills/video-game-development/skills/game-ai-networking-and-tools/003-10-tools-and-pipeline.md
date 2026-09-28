---
id: skill-10-tools-and-pipeline-1d1fd9c6ac
purpose: 10 tools and pipeline
source: src/vibey_tools/skills/plugins/video-game-development/skills/game-ai-networking-and-tools/SKILL.md
requires: ["skill-9-networking-0486640ecc"]
links: []
---

## §10. Tools and Pipeline

**[DURABLE] On any team past a few people, tools and iteration time determine your output
more than your engine choice does.** This is the most consistently under-invested area in
game development.

- **Iteration time is the metric that matters.** From "change a value" to "see it in the
  game": target **seconds**. A 10-minute rebuild-and-reload loop doesn't slow you by
  10 minutes — it eliminates the experimentation that finds the fun.
- **Hot reload** for scripts, shaders, and assets. Worth building.
- **Asset pipeline**: source assets (`.psd`, `.blend`, `.wav`) → **deterministic,
  cacheable import** → platform-optimized runtime format. **Never ship source formats.**
- **Content authoring in data, not code**, so designers can work without programmers and
  without a rebuild.
- **In-game debug tooling**: console, cheat commands, free camera, state visualizers,
  hitbox and navmesh overlays, AI state readouts, performance HUD. **Build these early;
  they pay for themselves within weeks.**
- **Version control**: **Perforce** remains the industry standard for large binary assets;
  **Git with LFS** works for smaller projects. ⚠️ Git handles large binaries badly and
  cannot lock files, which matters enormously when two artists edit the same `.uasset`.
- **Build system and CI**: automated builds per commit, on every target platform, with
  automated smoke tests. **A broken build blocks the whole team.**
