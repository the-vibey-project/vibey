---
id: skill-20-isa-design-11689599ef
purpose: 20 isa design
source: src/vibey_tools/skills/plugins/microarchitecture-and-memory-systems/skills/uarch-isa-simulation-measurement-roofline-and-specialization/SKILL.md
requires: []
links: ["skill-21-simulation-and-modelling-82074833cc"]
---

## §20. ISA Design

**⚠️ The RISC/CISC distinction is largely historical at the microarchitecture level** —
⚠️ **x86 decodes into internal micro-operations, so the execution core resembles a RISC
machine regardless.**
**⚠️ Where the ISA still matters**: ⚠️ **DECODE COMPLEXITY (⚠️ x86's variable-length
instructions make parallel decode genuinely harder, which is a real width constraint),
code density, the MEMORY MODEL (§8 → `uarch-caches-coherence-consistency-and-virtual-memory`), and extensibility.**
**⚠️ ARM's server rise** demonstrates that the ISA was never the barrier — ⚠️ **execution,
ecosystem and economics were.**
**⚠️ RISC-V**: ⚠️ **open, modular, extensible — with fragmentation as the standing risk and
profiles as the response.**
**⚠️ Extensions as the real battleground**: ⚠️ **vector, matrix, crypto and virtualization
extensions are where architectural competition actually happens now.**

---
