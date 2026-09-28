---
id: skill-6-real-time-discipline-67ad62c7a8
purpose: 6 real time discipline
source: src/vibey_tools/skills/plugins/flight-software/skills/flightsw-processors-radiation-and-real-time/SKILL.md
requires: ["skill-5-radiation-effects-in-software-terms-305dc6a1b1"]
links: ["skill-7-rtos-1e63e15db9"]
---

## §6. Real-Time Discipline

**[DURABLE] "Real-time" means bounded latency, not fast.**

**Hard** (missing a deadline is failure — attitude control, engine control),
**firm** (a missed deadline makes the result useless), **soft** (degradation).
⚠️ **Most flight software is hard real-time, and the deadlines are set by control-loop
stability margins** (§12 → `flightsw-gnc-verification-ground-and-autonomy`), not by preference.

**Scheduling**: **rate-monotonic** (⚠️ **static priorities by period; the RM bound is
`U ≤ n(2^(1/n) − 1)` → ~69% for large n, and schedulability is provable**), **EDF**
(dynamic, higher utilization, ⚠️ **but unpredictable overload behaviour**), **cyclic
executive** (⚠️ **a fixed time-sliced major/minor frame table — completely deterministic
and still widely used in launch vehicles for exactly that reason**), and **time-partitioned
(ARINC 653)** for mixed criticality.

**⚠️ Priority inversion is the canonical real-time bug, and it has flown.** A high-priority
task blocks on a mutex held by a low-priority task, which is preempted by a medium-priority
task. **Fix: priority inheritance or priority ceiling protocol.** See §16.1 → `flightsw-gnc-verification-ground-and-autonomy` — **this is what
happened to Mars Pathfinder on the surface of Mars.**

**WCET (worst-case execution time)** must be **bounded and analysed**, which is why
⚠️ **caches, branch prediction and speculative execution are a problem, not a benefit** —
they make timing statistical rather than bounded. **Some flight systems disable caches on
critical paths.**

**⚠️ Practices that follow**: no dynamic allocation (Power of 10 rule 3), **statically
allocated pools** if you need variable data, **bounded queues with defined overflow
behaviour**, **stack depth analysis with margin**, and **jitter measurement**, not just
average latency.

---
