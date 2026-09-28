---
id: skill-5-real-time-and-scheduling-6256ce9ef2
purpose: 5 real time and scheduling
source: src/vibey_tools/skills/plugins/automotive-software/skills/auto-real-time-safety-and-cybersecurity/SKILL.md
requires: []
links: ["skill-6-functional-safety-iso-26262-6140994c36"]
---

## §5. Real-Time and Scheduling

**⚠️ Deadlines are physical.** Engine control is crank-angle-synchronous; a stability-
control loop that misses its period has failed regardless of the answer.

**OSEK/AUTOSAR OS**: **statically configured tasks**, fixed priorities, **basic
(run-to-completion) vs extended (can wait)** tasks, **ISRs category 1 and 2**,
**resources with priority ceiling** (⚠️ **priority inversion is handled by the ceiling
protocol — see a flight-software reference §16.1 for what happens when it isn't**),
**alarms and counters**, **schedule tables** for time-triggered activation.

**⚠️ Analysis, not measurement, is what qualifies a design**: **rate-monotonic
schedulability**, **WCET** (⚠️ **bounded, and therefore caches and speculation are a
problem, not a benefit**), and **CAN worst-case response time analysis** — which combines
queuing delay, arbitration delay from higher-priority messages, and transmission time.

**⚠️ The multicore complication**: partitioning functions across cores, avoiding shared-
resource contention, and **memory protection between partitions of different ASIL.**
**Lockstep cores** for ASIL-D (§6.4).

---
