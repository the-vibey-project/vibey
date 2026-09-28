---
id: skill-1-mission-architecture-c4b20ceb50
purpose: 1 mission architecture
source: src/vibey_tools/skills/plugins/space-exploration/skills/space-mission-architecture-and-trajectory/SKILL.md
requires: ["skill-0-routing-79daa6ac2c"]
links: ["skill-2-trajectory-and-mission-design-b05dc3ed6e"]
---

## §1. Mission Architecture

### 1.1 The design cascade

**[DURABLE] Requirements flow downward and mass flows upward, and the loop closes only by
iteration:**
```
Science/mission objectives
  → measurement requirements → instrument selection
    → pointing, power, data volume, thermal requirements
      → bus sizing → power system → thermal system
        → mass and volume → launch vehicle and trajectory
          → ⚠️ which constrains everything above. Iterate.
```
**⚠️ The characteristic mistake is treating this as a waterfall.** It converges only if
you carry margins (§14.1 → `space-human-factors-life-support-and-reliability`) and re-run the loop when any element grows.

### 1.2 The architecture trades

| Trade | Poles |
|---|---|
| **Flyby / orbiter / lander / rover / sample return** | Cost and risk rise steeply; ⚠️ **so does science return per target** |
| **Single large vs. distributed small** | One capable spacecraft vs. constellations; ⚠️ **the latter buys simultaneity and graceful degradation** |
| **Solar vs. radioisotope** | §3 → `space-power-thermal-comms-and-navigation` — ⚠️ **decided largely by heliocentric distance and duty cycle** |
| **Chemical vs. electric propulsion** | §7 → `space-attitude-propulsion-and-edl` — time versus propellant mass |
| **Direct vs. gravity assist** | Δv versus flight time and window rigidity |
| **Crewed vs. robotic** | §16.1 → `space-reference` |
| **Store-and-forward vs. direct-to-Earth** | Relay orbiters transform surface data return (§5.4 → `space-power-thermal-comms-and-navigation`) |

### 1.3 ⚠️ Everything is mass

**[DURABLE] The conversion factors that make this concrete:**
- **Power**: solar arrays run **~50–150 W/kg** at 1 AU (BOL, including structure);
  **RTGs ~2–5 W/kg**. Batteries **~100–250 Wh/kg**.
- **Data rate**: gain scales as `D²`, so doubling downlink means a bigger dish or more
  transmit power — **and transmit power means more array and more radiator** (§5 → `space-power-thermal-comms-and-navigation`).
- **Redundancy**: full block redundancy roughly **doubles** the subsystem mass.
- **Consumables**: **~5 kg/person/day** of food, water and oxygen open-loop —
  ⚠️ **which is why closure ratio dominates crewed mission mass** (§10.2 → `space-human-factors-life-support-and-reliability`).

**⚠️ And propellant mass is exponential in Δv** (see a rocket-science reference §1), so a
kilogram added to a Mars lander costs several kilograms in Earth departure stage.

---
