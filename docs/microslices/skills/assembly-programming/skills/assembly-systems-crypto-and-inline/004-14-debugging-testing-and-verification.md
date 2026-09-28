---
id: skill-14-debugging-testing-and-verification-c04e45f162
purpose: 14 debugging testing and verification
source: src/vibey_tools/skills/plugins/assembly-programming/skills/assembly-systems-crypto-and-inline/SKILL.md
requires: ["skill-13-inline-assembly-and-intrinsics-ead05708cd"]
links: []
---

## §14. Debugging, Testing, and Verification

**Debugging**: `gdb`/`lldb` with `layout asm` / `si` / `info registers` / `x/i $pc`;
`disassemble /s` to interleave source; hardware watchpoints; `rr` for reverse debugging
(x86 Linux — transformative for "how did this register get that value"); Intel PT / Arm
CoreSight for execution traces; and single-stepping is the ultimate ground truth.

**Testing hand-written assembly**:
- **Differential testing** against a simple, obviously-correct C reference over random
  inputs. **This is the single most valuable practice** and catches the overwhelming
  majority of real bugs.
- **Exhaustive testing on small input spaces** where feasible.
- **Edge cases**: zero length, one element, unaligned, maximum values, sign boundaries,
  overlapping buffers, and the tail-handling path (which is where SIMD bugs concentrate).
- **Sanitizers won't help you.** ASan and MSan don't instrument your assembly; you're
  outside their model.
- **Valgrind can still catch** bad memory access and uninitialized-value use in some cases.
- **Verify ABI compliance mechanically**: a wrapper that fills every callee-saved register
  with a poison value, calls your routine, and checks them afterwards will catch clobbering
  bugs that otherwise surface as corruption three functions away.
- **Test on multiple microarchitectures.** Something that's a win on one core is a loss on
  another, and something that's *correct* on one may expose a memory-ordering bug on
  another (§1.4 → `assembly-fundamentals-and-isas`).

**Formal verification** is real in this niche: **Alive2** for peephole correctness,
**Vale** and **Jasmin** for verified crypto assembly, **HACL\*** and **fiat-crypto** for
verified implementations that *generate* the assembly. If you're writing crypto assembly
by hand in 2026 without a verification story, consider whether you should be.
