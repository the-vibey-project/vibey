---
id: skill-11-real-time-and-safety-critical-engineering-7fd6545d56
purpose: 11 real time and safety critical engineering
source: src/vibey_tools/skills/plugins/robotics-software/skills/robotics-safety-standards-and-deployment/SKILL.md
requires: []
links: ["skill-12-testing-debugging-and-deployment-070457cd15"]
---

## §11. Real-Time and Safety-Critical Engineering

**[DURABLE] "Real-time" means deterministic, not fast.** A system that responds in 10ms
every single time is real-time; one that averages 1ms and occasionally takes 100ms is not.
**Hard real-time** means a missed deadline is a system failure.

**How you actually get it**: **PREEMPT_RT** (mainlined into Linux, and the common
foundation), a genuine **RTOS** (QNX, VxWorks, Zephyr, FreeRTOS) for the hard layers,
**⚠️ CPU isolation and shielding** (`isolcpus`, IRQ affinity) so your control thread owns a
core, **memory locking** (`mlockall`) and **no allocation in the control loop**,
**priority inheritance** on any shared mutex, and **⚠️ lock-free structures for
producer-consumer across priority levels.**

> **⚠️ GOTCHA — the things that silently destroy determinism:** dynamic memory allocation,
> unbounded loops, `printf` and logging in the hot path, page faults, garbage collection,
> **CPU frequency scaling and thermal throttling**, network stack processing on your
> control core, and **priority inversion**. ⚠️ **Measure worst-case, not average — the
> distribution's tail is the whole specification.**

**Architecturally**: separate the **safety-critical** path from the **mission** path, and
run them at different assurance levels. ⚠️ **A watchdog with an independent path to
actuator power is the last line of defence and it must not depend on the software it's
watching.**

---
