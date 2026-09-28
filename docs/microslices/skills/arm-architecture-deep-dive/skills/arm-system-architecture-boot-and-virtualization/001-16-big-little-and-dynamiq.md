---
id: skill-16-big-little-and-dynamiq-8ac7aa694f
purpose: 16 big little and dynamiq
source: src/vibey_tools/skills/plugins/arm-architecture-deep-dive/skills/arm-system-architecture-boot-and-virtualization/SKILL.md
requires: []
links: ["skill-17-interrupts-and-timers-031b369577"]
---

## §16. big.LITTLE and DynamIQ

**⚠️ Heterogeneous cores sharing one ISA** — ⚠️ **the property that makes it work is that
all cores are architecturally identical, so a thread can migrate mid-execution.**
> **⚠️ GOTCHA — and this is exactly what Intel's hybrid designs got wrong initially.**
> ⚠️ **If the big and little cores support DIFFERENT feature sets, a thread using a feature
> present only on one cannot migrate — which is why Intel disabled AVX-512 on its
> performance cores when the efficiency cores lacked it.** **⚠️ ARM's insistence on
> architectural uniformity across a DynamIQ cluster avoids the problem by construction.**

**⚠️ The scheduling problem is the hard part** — ⚠️ **the OS must decide placement, and
Energy Aware Scheduling uses a power model to do it.** ⚠️ **Getting this wrong produces the
classic symptom of a fast chip that feels slow.**
**⚠️ DynamIQ** replaced the original cluster arrangement, ⚠️ **allowing mixed core types in
one coherent cluster with shared L3 and per-core power control.**

---
