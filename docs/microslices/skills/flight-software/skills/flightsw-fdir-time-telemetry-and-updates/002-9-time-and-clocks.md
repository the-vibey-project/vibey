---
id: skill-9-time-and-clocks-d1af8fec66
purpose: 9 time and clocks
source: src/vibey_tools/skills/plugins/flight-software/skills/flightsw-fdir-time-telemetry-and-updates/SKILL.md
requires: ["skill-8-fdir-802e1f6675"]
links: ["skill-10-command-and-telemetry-2986c1116f"]
---

## §9. Time and Clocks

**[DURABLE] Getting time wrong is a classic and expensive failure mode.**

**Time scales**: **TAI** (atomic, continuous — ⚠️ **what you want onboard**), **UTC**
(⚠️ **has leap seconds; do not use it as an onboard timebase**), **GPS time** (continuous,
offset from TAI by 19 s), **spacecraft elapsed time (SCET/MET)** — ⚠️ **a free-running
onboard counter, which is the actual reference for onboard operations.**

**⚠️ Clock correlation** is the operational task: relating the onboard counter to ground
time using radiometric measurements, and tracking **drift and drift rate**. Every
science observation timestamp depends on it.

**⚠️ The specific hazards:**
- **Leap seconds** — ⚠️ **a repeated or skipped second breaks naive monotonic
  assumptions.** Multiple terrestrial outages have been caused by this; **don't inherit
  the problem onboard.**
- **Counter rollover** — ⚠️ **a 32-bit millisecond counter wraps in 49.7 days.** The
  Patriot missile timing failure and several spacecraft anomalies trace to accumulated or
  wrapped counters. **Compute the wrap interval explicitly and handle it.**
- **Light-time correction** — a command's execution time and an observation's timestamp
  are in different frames; ⚠️ **one-way light time to Mars is 3–22 minutes.**
- **Relativistic corrections** — ⚠️ **GPS requires them (about 38 μs/day net); for precision
  deep-space navigation they are not optional.**

---
