---
id: skill-2-the-game-loop-52f0d8cfc2
purpose: 2 the game loop
source: src/vibey_tools/skills/plugins/video-game-development/skills/game-engines-loop-and-architecture/SKILL.md
requires: ["skill-1-engines-2a88518910"]
links: ["skill-3-code-architecture-cb4275d87e"]
---

## §2. The Game Loop

### 2.1 The structure

```
while (running) {
    processInput();
    while (accumulator >= FIXED_DT) {   // fixed-step simulation
        update(FIXED_DT);
        accumulator -= FIXED_DT;
    }
    render(accumulator / FIXED_DT);      // interpolate between sim states
}
```

**[DURABLE] "Fix Your Timestep!" (Glenn Fiedler) is the single most-referenced article in
game programming, and for good reason.** The variants and their failure modes:

| Approach | Problem |
|---|---|
| **Variable delta time everywhere** | Physics behaves differently at different framerates. Non-deterministic. **Tunneling at low fps.** Simple, and wrong for anything with physics |
| **Fixed timestep, no interpolation** | Deterministic but produces visible judder when render rate ≠ sim rate |
| **Fixed timestep + accumulator + render interpolation** | **The standard correct answer.** Deterministic sim, smooth render |
| **Semi-fixed with a max frame time clamp** | Necessary in practice — prevents the "spiral of death" |

> **⚠️ GOTCHA — the spiral of death.** If a frame takes longer than real time, the
> accumulator grows, so you run more sim steps, so the frame takes longer still. **Always
> clamp the maximum accumulated time** (e.g. never simulate more than 5 steps in one
> frame) and accept slow-motion over a freeze. Every engine that skips this eventually
> hangs on someone's machine.

### 2.2 Determinism

**[DURABLE] You need determinism for**: rollback netcode (§9.3 → `game-ai-networking-and-tools`), replays, lockstep
multiplayer, reproducible bug reports, and automated testing. It is much easier to design
in than to add later.

Requirements: **fixed timestep**, **fixed iteration order** (⚠️ hash-map iteration order is
the classic determinism bug), a **seeded, explicitly-managed RNG** (separate streams for
simulation and cosmetics), and **no floating-point divergence** across platforms — which
is the hard one, since compiler flags, `x87` vs. SSE, FMA contraction, and library
implementations of `sin`/`cos` all differ. **Fixed-point arithmetic** is the sledgehammer
answer, used by many fighting games and RTSs for exactly this reason.

---
