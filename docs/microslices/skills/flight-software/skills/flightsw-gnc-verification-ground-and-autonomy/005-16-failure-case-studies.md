---
id: skill-16-failure-case-studies-ea6529494f
purpose: 16 failure case studies
source: src/vibey_tools/skills/plugins/flight-software/skills/flightsw-gnc-verification-ground-and-autonomy/SKILL.md
requires: ["skill-15-autonomy-and-onboard-ai-86c34ad723"]
links: []
---

## §16. Failure Case Studies

**[DURABLE] Each of these produced a rule that is now standard practice. This is how the
discipline was built.**

**16.1 ⚠️ Mars Pathfinder (1997) — priority inversion, in flight, on Mars.**
The lander began experiencing total system resets on the surface. **Cause: a high-priority
bus management task blocked on a mutex held by a low-priority meteorological task, which
was preempted by a medium-priority communications task.** The watchdog fired and reset the
system. **⚠️ The fix was uplinked: enable priority inheritance on that mutex — a flag that
existed in VxWorks and was off.** **The lesson: priority inheritance is not optional, and
the ability to debug and patch in flight saved the mission** (§11 → `flightsw-fdir-time-telemetry-and-updates`).

**16.2 ⚠️ Ariane 501 (1996) — reuse without re-validation.**
A 64-bit float horizontal-velocity value was converted to a 16-bit signed integer. The
Ariane 5 trajectory produced a value that overflowed; **the exception was unhandled, both
(identical, redundant) inertial reference systems shut down, the backup failed first and
the primary a moment later, and the vehicle self-destructed 37 seconds after liftoff.**
⚠️ **The computation was Ariane 4 alignment code that served no purpose after liftoff on
Ariane 5.** **Lessons: identical redundancy does not protect against a design fault;
inherited code must be re-validated against the new operating envelope; and dead code
should be dead.**

**16.3 ⚠️ Mars Climate Orbiter (1999) — units at an interface.**
Ground software produced impulse in **pound-force-seconds**; the navigation software
expected **newton-seconds.** Trajectory errors accumulated across the cruise and the
spacecraft entered the atmosphere too low. **Lesson: interfaces need explicitly specified
units, and unit-typed values in code where the language permits it.**

**16.4 ⚠️ Mars Polar Lander (1999) — a sensor transient believed too readily.**
Leg-deployment vibration is believed to have generated a spurious touchdown signal; the
software latched it and **cut the descent engines ~40 m above the surface.** ⚠️ **Lesson:
plausibility-check sensor inputs against other state — touchdown at 40 m altitude was
physically impossible and could have been rejected.**

**16.5 ⚠️ Therac-25 (1985–87) — outside aerospace, and required reading anyway.**
Race conditions in a radiation therapy machine's software, with hardware interlocks removed
in favour of software checks, caused massive overdoses and deaths. **Lesson: removing
hardware interlocks because "the software handles it" is a specific and recurring failure
mode, and concurrency bugs are not theoretical.**

**16.6 ⚠️ Boeing Starliner OFT-1 (2019) — clock initialization.**
The mission elapsed timer initialized from the launch vehicle at the wrong point,
**offset by 11 hours**, causing the spacecraft to burn propellant in the wrong mission
phase. ⚠️ **A second, separate software defect in the service module separation sequence
was found and patched during the flight** — which would have caused a destructive
recontact. **Lesson: end-to-end integrated testing of the full sequence, not
subsystem-by-subsystem.**

**⚠️ The pattern across all of them**: none was an exotic algorithmic error. **They were
interfaces, initialization, inherited assumptions, concurrency, and inadequate integrated
testing.** That is where flight software actually fails.
