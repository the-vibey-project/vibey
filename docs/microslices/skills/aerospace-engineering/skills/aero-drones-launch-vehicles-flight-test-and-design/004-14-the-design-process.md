---
id: skill-14-the-design-process-4ce115cf65
purpose: 14 the design process
source: src/vibey_tools/skills/plugins/aerospace-engineering/skills/aero-drones-launch-vehicles-flight-test-and-design/SKILL.md
requires: ["skill-13-flight-test-and-certification-76d2ba78e8"]
links: []
---

## §14. The Design Process

**⚠️ Conceptual → preliminary → detail, and the first phase locks in most of the cost.**
```
Requirements (payload, range, speed, field length, regulation)
  → ⚠️ THE SIZING LOOP: guess weight → estimate L/D and SFC → Breguet (§5)
    → fuel fraction → new weight → iterate to convergence
      → wing loading W/S and thrust loading T/W from constraint analysis
        → configuration → detail design → test → certify
```
**⚠️ The constraint diagram is the central design tool**: plot `T/W` against `W/S` with
lines for takeoff distance, climb gradient, cruise, ceiling and landing. ⚠️ **The feasible
region is bounded, and the design point is usually the lowest `T/W` that satisfies
everything — because thrust is expensive.**

**⚠️ Weight estimation is where programmes are won or lost**: statistical relations early,
component build-up later, ⚠️ **and weight growth during development is close to a law of
nature — carrying explicit margin is professional practice, not pessimism.**
**Multidisciplinary optimization (MDO)** couples aero, structures, propulsion and control
because ⚠️ **optimizing them separately gives a worse aircraft than optimizing them
together — the couplings are strong.**
