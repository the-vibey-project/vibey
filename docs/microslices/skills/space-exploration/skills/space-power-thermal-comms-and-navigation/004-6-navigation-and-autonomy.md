---
id: skill-6-navigation-and-autonomy-3c0bd6faa0
purpose: 6 navigation and autonomy
source: src/vibey_tools/skills/plugins/space-exploration/skills/space-power-thermal-comms-and-navigation/SKILL.md
requires: ["skill-5-communications-95cae00d64"]
links: []
---

## §6. Navigation and Autonomy

### 6.1 Deep space navigation

**[DURABLE] Three measurement types, and they're complementary:**
- **Doppler** — line-of-sight velocity from carrier frequency shift. ⚠️ **Precise to
  ~0.1 mm/s**, and the workhorse.
- **Ranging** — round-trip time of a modulated code. Metres at planetary distance.
- **⚠️ Delta-DOR** (Delta Differential One-way Ranging) — two stations observe the
  spacecraft and a quasar alternately; **differencing removes common errors and gives
  plane-of-sky position to nanoradians.** This is what makes precision arrival possible.

**Optical navigation** — imaging the target against background stars, essential for
approach and for small bodies where the ephemeris is poor.

**⚠️ Onboard**: star trackers (arcsecond attitude), sun sensors, IMUs (⚠️ **drift, always**),
and for landing, **terrain-relative navigation** — matching descent imagery against
orbital maps in real time. **Perseverance's TRN is what allowed landing in Jezero's
hazardous terrain**, which earlier missions would have had to avoid.

### 6.2 Autonomy

**[DURABLE] Autonomy is not a nicety at distance; it's forced by §5.3.**

**The levels in practice**: **sequenced execution** (a time-tagged command load — the
historical default), **event-driven sequencing**, **onboard planning** (⚠️ **the Remote
Agent experiment on Deep Space 1 in 1999 was the first onboard planner in control of a
spacecraft**), **autonomous science** (AEGIS on the Mars rovers selects and targets
spectroscopy without ground involvement), and **fully autonomous EDL** (§8 → `space-attitude-propulsion-and-edl`).

**⚠️ Fault protection is the hardest part, and it's what actually keeps spacecraft alive**:
- **Safe mode** — power-positive, thermally stable, Earth-pointed, awaiting instructions.
  ⚠️ **Every deep space mission enters safe mode. The design question is whether it can
  survive there indefinitely.**
- **Watchdogs and command loss timers** — ⚠️ **if no command is received for N days, assume
  a fault and reconfigure.** This has saved missions whose primary receivers failed.
- **Redundancy management** and autonomous swap to the B-side string.
- **⚠️ Fault protection that misfires is itself a hazard** — a spurious safe-mode entry
  during a critical event (an orbit insertion burn) can lose the mission.
