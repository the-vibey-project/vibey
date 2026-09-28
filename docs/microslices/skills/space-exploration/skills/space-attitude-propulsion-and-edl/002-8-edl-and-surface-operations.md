---
id: skill-8-edl-and-surface-operations-f75329a97a
purpose: 8 edl and surface operations
source: src/vibey_tools/skills/plugins/space-exploration/skills/space-attitude-propulsion-and-edl/SKILL.md
requires: ["skill-7-attitude-control-and-in-space-propulsion-f21a28680f"]
links: []
---

## §8. EDL and Surface Operations

**[DURABLE] Entry heating physics is in a rocket-science reference §12. What matters here
is the sequence and why it's hard.**

**⚠️ Mars EDL is the canonical hard case, and the reason is a genuine physical squeeze:**
the atmosphere is **~1% of Earth's** — thick enough to demand a heat shield, **too thin to
slow you to safe landing speed with parachutes alone.** Venus and Titan are easier
(dense atmospheres); the Moon and asteroids are easier (no atmosphere, pure propulsive).

**The Mars sequence, roughly seven minutes:**
```
Entry interface (~125 km, ~5.5–7.5 km/s)
  → peak heating (~100 s), peak deceleration (~8–15 g)
    → supersonic parachute deploy (Mach 1.5–2.2, ~10 km)   ⚠️ narrow box
      → heat shield jettison → radar/TRN acquisition
        → backshell separation → powered descent
          → touchdown: legs, airbags, or sky crane
```
**⚠️ Everything is autonomous** (§5.3 → `space-power-thermal-comms-and-navigation`) — the vehicle has landed or crashed before the
first telemetry arrives.

**Landing methods and their regimes**: **airbags** (Pathfinder, MER — ⚠️ **mass-efficient
but caps landed mass around a few hundred kg and requires benign terrain**), **legs**
(Viking, Phoenix, InSight — ⚠️ **engine plume excavates regolith and can contaminate
samples**), **sky crane** (MSL, Perseverance — ⚠️ **bizarre-looking and the correct answer
for ~1-tonne rovers: it keeps the engines away from the surface and puts the wheels down
directly**).

**⚠️ The landed-mass ceiling**: Mars EDL has historically capped landed mass near
**~1 tonne**, because parachute area scales badly and supersonic retropropulsion was
unproven. **Scaling past it requires either much larger decelerators or supersonic
retropropulsion**, which is the central open EDL problem (§17 → `space-reference`).

**Surface operations**: **mobility** (rocker-bogie suspension — ⚠️ **passively keeps six
wheels loaded on rough terrain, no active control**), ⚠️ **wheel wear**, which was a real
mission-shaping problem for Curiosity, **dust** (⚠️ **abrasive, electrostatic, and
mission-ending for solar-powered landers**), **thermal cycling**, **sample acquisition**
(drilling in vacuum or low gravity is genuinely hard — ⚠️ **InSight's mole failed because
Martian regolith didn't provide expected friction**), and **traverse planning** under
light-time (§6.2 → `space-power-thermal-comms-and-navigation`).
