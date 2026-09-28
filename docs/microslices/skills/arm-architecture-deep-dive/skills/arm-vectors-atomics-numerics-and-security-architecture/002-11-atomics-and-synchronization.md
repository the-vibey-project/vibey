---
id: skill-11-atomics-and-synchronization-e0d96328c9
purpose: 11 atomics and synchronization
source: src/vibey_tools/skills/plugins/arm-architecture-deep-dive/skills/arm-vectors-atomics-numerics-and-security-architecture/SKILL.md
requires: ["skill-10-vector-extensions-b317a92a3c"]
links: ["skill-12-floating-point-and-numerics-99f75889ce"]
---

## §11. Atomics and Synchronization

**⚠️ The original mechanism is LOAD-EXCLUSIVE / STORE-EXCLUSIVE (LDXR/STXR)** —
⚠️ **an optimistic pair with a retry loop, which is flexible and scales badly under
contention because every failure means another round trip.**
**⚠️ LSE (Large System Extensions, ARMv8.1)** added ⚠️ **true single-instruction atomics —
LDADD, SWP, CAS and relatives — which perform far better under high core counts, and are
frequently done at the interconnect or cache rather than by the core.**
> **⚠️ GOTCHA — this is a real and measurable performance cliff.** ⚠️ **Code compiled without
> LSE enabled falls back to exclusive loops, and on a high-core-count server the difference
> under contention is substantial.** **⚠️ Check your compiler flags (`-moutline-atomics` or
> an explicit `-march`), because the default may target the oldest baseline.**

**⚠️ WFE/WFI and SEV** — ⚠️ **wait-for-event and send-event, which let a spinning core sleep
until something changes rather than burning power.**
**⚠️ Combine with §8 → `arm-aarch64-exception-levels-memory-model-and-mmu`'s acquire/release forms** — ⚠️ **LDADDAL and friends carry ordering
semantics in the instruction.**

---
