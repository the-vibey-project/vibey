---
id: skill-12-combinational-building-blocks-018455c32e
purpose: 12 combinational building blocks
source: src/vibey_tools/skills/plugins/digital-logic-and-firmware-engineering/skills/logic-standard-cells-boolean-minimization-and-arithmetic/SKILL.md
requires: ["skill-11-minimization-8b7ee9f5cc"]
links: ["skill-13-arithmetic-circuits-5ba49f85b1"]
---

## §12. Combinational Building Blocks

**⚠️ The standard vocabulary**: ⚠️ **multiplexer (⚠️ and note a mux is functionally
complete — you can build any logic from muxes, which is exactly what an FPGA LUT does),
demultiplexer, decoder, encoder, priority encoder, comparator, barrel shifter, parity
generator.**
**⚠️ Tri-state buffers and buses** — ⚠️ **and the warning that on-chip tri-state buses have
largely been replaced by multiplexers, because bus contention is a real failure and
floating nodes are worse.**
**⚠️ ROM and PLA/PAL** as ways of implementing arbitrary combinational functions by lookup
rather than by gates — ⚠️ **the conceptual ancestor of the FPGA.**
**⚠️ The design instinct worth building**: ⚠️ **most "complicated" combinational logic
decomposes into these blocks, and expressing it that way both reads better and synthesizes
better than a pile of gates.**

---
