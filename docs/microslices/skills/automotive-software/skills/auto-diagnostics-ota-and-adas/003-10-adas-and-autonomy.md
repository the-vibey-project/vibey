---
id: skill-10-adas-and-autonomy-2c60d92366
purpose: 10 adas and autonomy
source: src/vibey_tools/skills/plugins/automotive-software/skills/auto-diagnostics-ota-and-adas/SKILL.md
requires: ["skill-9-flashing-and-ota-0e162e1b01"]
links: []
---

## §10. ADAS and Autonomy

### 10.1 The SAE levels — precisely
```
L0  no automation                    L1  ⚠️ ONE of steering OR speed (ACC, or lane keep)
L2  ⚠️ BOTH steering AND speed — but the DRIVER MONITORS AND IS RESPONSIBLE
L3  ⚠️ conditional — the SYSTEM monitors; driver may disengage but must take over
    on request, within a defined ODD
L4  high — no driver takeover needed WITHIN the ODD
L5  full — any condition a human could manage
```
> **⚠️ GOTCHA — the L2/L3 boundary is a liability boundary, not a capability one.**
> **At L2 the human is legally the driver and is monitoring.** At L3, **the system is
> driving and the manufacturer's exposure changes fundamentally.** ⚠️ **This is why
> systems that feel very capable are still marketed and certified as L2** — and why
> marketing language ("Autopilot", "Full Self-Driving (Supervised)") has attracted
> regulatory attention. **The number is about who is responsible when it fails.**
>
> **⚠️ And L3's hand-back problem is genuinely hard**: a driver who has been out of the
> loop needs seconds to regain situational awareness, so the system must detect its own
> impending limit far enough ahead to give a safe transition — **and must have a fallback
> if the driver doesn't respond.**

**ODD (Operational Design Domain)** — ⚠️ **the explicit statement of where the system is
valid**: road types, speeds, weather, lighting, geography. **The ODD is the safety
argument's foundation; a system outside its ODD has no claim at all.**

### 10.2 The stack
```
SENSE     camera, radar (⚠️ robust in weather, poor resolution), lidar (⚠️ precise
          geometry, cost and weather-limited), ultrasonic, IMU, GNSS, HD map
   ↓
PERCEIVE  detection, classification, tracking, ⚠️ SENSOR FUSION
   ↓
LOCALIZE  where am I, to sub-metre — GNSS + map matching + odometry
   ↓
PREDICT   ⚠️ what will other agents do — the hardest part, and the one that
          separates competent systems from dangerous ones
   ↓
PLAN      route → behaviour → trajectory
   ↓
CONTROL   lateral and longitudinal actuation
```
**⚠️ The camera-vs-lidar argument is a genuine engineering disagreement**, not settled:
cameras are cheap and information-rich but must *infer* depth; lidar measures it directly
but costs more and degrades in weather. **Radar is the underrated one — it works when the
others don't, and it directly measures velocity via Doppler.** **Most manufacturers use
fusion; at least one prominent one bet on vision-only.** ⚠️ **The outcome is not yet
decided by evidence available to outsiders.**

### 10.3 Safety architecture for autonomy
**⚠️ The pattern that works, and it mirrors robotics and flight software**: a learned,
high-capability nominal path **inside a classical, verifiable safety envelope.**
- **Redundancy and diversity** — independent sensing paths, so a common failure mode
  doesn't take out perception entirely.
- **Fail-operational, not just fail-safe** — ⚠️ **at L3+ you cannot simply shut down;
  the vehicle must reach a minimal risk condition under its own control**, which means
  redundant power, steering and braking paths.
- **⚠️ A safety monitor / doer-checker**: a simpler, verifiable supervisor that can veto
  the complex planner. **This is how you get an ASIL claim out of a system containing a
  neural network you cannot formally verify.**
- **Driver monitoring** at L2 — ⚠️ **camera-based gaze tracking is now the expected
  implementation, because torque-sensing steering-wheel checks are trivially defeated.**

### 10.4 ⚠️ The validation problem
**You cannot drive your way to a safety claim.** Demonstrating a fatality rate better than
human by brute-force road miles requires **billions of miles** — statistically prohibitive
and impossible to repeat per software revision.

**⚠️ So the industry uses a combination, and none of it is fully satisfying**: scenario-
based testing against catalogues, **simulation at enormous scale** (with the sim-to-real
gap as the standing objection), **shadow mode** (run the system without acting and compare
to the human), disengagement metrics (⚠️ **easily gamed and not comparable across
companies**), and the SOTIF framework (§6.5 → `auto-real-time-safety-and-cybersecurity`) for reasoning about unknowns.
**⚠️ There is no accepted, sufficient validation methodology for full autonomy. Anyone
claiming otherwise is overstating.**
