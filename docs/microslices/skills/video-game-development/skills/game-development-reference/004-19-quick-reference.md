---
id: skill-19-quick-reference-f4b6eaff7e
purpose: 19 quick reference
source: src/vibey_tools/skills/plugins/video-game-development/skills/game-development-reference/SKILL.md
requires: ["skill-18-the-canon-9dc5577ce1"]
links: ["skill-20-sources-and-method-4ba051070b"]
---

## §19. Quick Reference

### 19.1 Numbers
- **60 fps = 16.67 ms; 120 fps = 8.33 ms; 30 fps = 33.3 ms.**
- Motion-to-photon: **<30 ms crisp, 50–100 ms typical, >150 ms broken.**
- Entity interpolation delay: **~100 ms** behind server time.
- Rollback re-simulation budget: **7–10 frames within one frame.**
- Localization text expansion: **German ≈ +30%** over English.
- Console cert: **budget weeks; expect a rejection.**
- Scope rule: **estimate honestly, then cut half.**
- The last **10%** of the game is **50%** of the work.

### 19.2 Project start checklist
- [ ] Engine chosen for platform, genre, team experience, **and licence risk** — terms read and archived
- [ ] Fixed timestep with accumulator and a max-step clamp, from day one
- [ ] Determinism decided (needed for rollback, replays, lockstep, regression tests)
- [ ] Multiplayer architecture decided **now**, if there will ever be multiplayer
- [ ] Version control appropriate to your asset sizes (Perforce vs. Git LFS)
- [ ] CI building every target platform per commit
- [ ] Iteration loop measured in seconds, not minutes
- [ ] In-game debug console and state visualizers scaffolded early
- [ ] Console cert requirements read (suspend/resume and save integrity especially)
- [ ] Accessibility baseline planned: remapping, subtitles, colourblind-safe, screen-shake toggle
- [ ] Platform AI-disclosure obligations understood if using generative tools
- [ ] Steam page up early; wishlists accumulating
- [ ] Vertical slice scoped as the first milestone

### 19.3 "It runs badly" triage
| Symptom | First look |
|---|---|
| Low average framerate | Profile CPU vs GPU first — you're optimizing the wrong one otherwise |
| Periodic hitches | Allocation/GC, shader compilation, asset streaming, or level loading |
| Stutter only on first play of an area | **Shader/PSO compilation** (§4.3 → `game-rendering-physics-animation-and-audio`) |
| Fine on your machine, bad for players | You profiled on the wrong hardware |
| GPU-bound | Overdraw, resolution, shader complexity, bandwidth |
| CPU-bound on the render thread | Draw calls and submission — batch and instance |
| CPU-bound in gameplay | Cache misses, per-frame allocation, O(n²) queries, unbudgeted pathfinding |
| Physics spikes | Too many active bodies, CCD everywhere, timestep too small |
| Memory growth over a session | Leak, or pool that never returns — soak test |

---
