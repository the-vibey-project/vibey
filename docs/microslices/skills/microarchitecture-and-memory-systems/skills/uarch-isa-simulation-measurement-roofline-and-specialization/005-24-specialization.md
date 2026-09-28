---
id: skill-24-specialization-9433486afc
purpose: 24 specialization
source: src/vibey_tools/skills/plugins/microarchitecture-and-memory-systems/skills/uarch-isa-simulation-measurement-roofline-and-specialization/SKILL.md
requires: ["skill-23-roofline-and-fundamental-limits-abf5a4bc78"]
links: []
---

## §24. Specialization

**⚠️ Why fixed-function hardware exists**: ⚠️ **removing generality removes fetch, decode,
speculation and coherence overhead, and the energy efficiency gain over a general-purpose
core can be orders of magnitude for a well-matched task.**
**⚠️ The trade** is flexibility, and ⚠️ **the risk is that the workload moves faster than
the silicon cycle — a genuine problem for AI accelerators specifically, where model
architectures change faster than chips ship.**
**⚠️ The spectrum**: ⚠️ **CPU → SIMD → GPU → programmable accelerator → FPGA → fixed-function
ASIC**, with programmability falling and efficiency rising.
**⚠️ Domain-specific architecture** (Hennessy and Patterson's framing) is ⚠️ **the
mainstream answer to the end of Dennard scaling — since you cannot power all the
transistors anyway (dark silicon), spend them on specialized units used intermittently.**
