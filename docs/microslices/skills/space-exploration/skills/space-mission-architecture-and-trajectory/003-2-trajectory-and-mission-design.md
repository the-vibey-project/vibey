---
id: skill-2-trajectory-and-mission-design-b05dc3ed6e
purpose: 2 trajectory and mission design
source: src/vibey_tools/skills/plugins/space-exploration/skills/space-mission-architecture-and-trajectory/SKILL.md
requires: ["skill-1-mission-architecture-c4b20ceb50"]
links: []
---

## §2. Trajectory and Mission Design

**[DURABLE] Orbital mechanics proper is in a rocket-science reference §7. What matters
here is the mission-level consequence.**

**Launch windows** are set by planetary geometry. **Mars synodic period ≈ 25.6 months** —
⚠️ **miss the window and you wait over two years**, which is the single hardest scheduling
constraint in planetary exploration and the reason Mars programmes slip in two-year
quanta.

**Porkchop plots** — contours of C₃ (launch energy) and arrival `v_∞` over departure and
arrival dates. ⚠️ **The working tool of mission design**: they show simultaneously what the
launch vehicle must deliver and what the arrival must absorb.

**Gravity assists** buy Δv at the cost of rigidity and flight time. **Cassini's
VVEJGA** (Venus-Venus-Earth-Jupiter) took ~7 years to Saturn; **direct would have needed a
launch vehicle that didn't exist.** ⚠️ **Assists don't just save propellant — they enable
missions outright**, and they make the launch window nearly immovable.

**Low-energy transfers** via weak-stability boundaries cost less Δv and much more time.

**Orbit selection at the target**: **circular vs. elliptical** (⚠️ **elliptical is far
cheaper to enter and gives varied altitude coverage; circular gives uniform resolution**),
**polar vs. equatorial** (coverage vs. Δv), **frozen orbits** for stability,
**sun-synchronous** for consistent lighting, and **halo orbits at L1/L2** (⚠️ **thermally
stable, continuous sky access, and the reason JWST is at Sun-Earth L2** — with the cost
that it's unreachable for servicing).

**⚠️ Aerocapture** — using a single atmospheric pass to enter orbit — offers enormous Δv
savings and **has never been flown.** Aerobraking (many shallow passes over months) has
been, repeatedly, at Mars and Venus. **The difference is that aerobraking is
incrementally correctable and aerocapture is one shot.**
