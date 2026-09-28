---
id: skill-5-other-isas-worth-knowing-4a37752128
purpose: 5 other isas worth knowing
source: src/vibey_tools/skills/plugins/assembly-programming/skills/assembly-fundamentals-and-isas/SKILL.md
requires: ["skill-4-risc-v-158f761c5f"]
links: []
---

## §5. Other ISAs Worth Knowing

| ISA | Where you'll meet it |
|---|---|
| **ARM32 / Thumb-2** | Older embedded, Cortex-M. Thumb-2's mixed 16/32-bit encoding is excellent for code density; **Cortex-M is Thumb-only** |
| **AVR** | Arduino, 8-bit MCUs. Harvard architecture — separate code and data address spaces, which surprises everyone |
| **MSP430, PIC, 8051** | Deeply embedded, still shipping in volume |
| **POWER / PowerPC** | IBM servers, older consoles. Weak memory model, big-endian heritage |
| **MIPS** | Networking silicon, older Roku/embedded, and **every undergraduate architecture course** |
| **SPARC** | Register windows — a genuinely different idea worth understanding |
| **s390x** | IBM mainframe. Big-endian, and still absolutely everywhere in banking |
| **WebAssembly** | A stack machine and a compile target, not hardware. Structured control flow, no registers |
| **x86 16/32-bit** | Boot code, BIOS/UEFI, DOS-era reverse engineering, retro |
| **GPU ISAs** (PTX/SASS, RDNA, SPIR-V) | Mostly generated; PTX is a virtual ISA, SASS is the real one |
| **6502, Z80, 68000** | Retro computing and demoscene, and the best teaching ISAs ever made |
