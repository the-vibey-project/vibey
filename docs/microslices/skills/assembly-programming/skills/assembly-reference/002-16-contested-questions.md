---
id: skill-16-contested-questions-45d015266e
purpose: 16 contested questions
source: src/vibey_tools/skills/plugins/assembly-programming/skills/assembly-reference/SKILL.md
requires: ["skill-15-anti-patterns-d7d96fdbe5"]
links: ["skill-17-currency-snapshot-verified-august-2026-ae617ba534"]
---

## §16. Contested Questions

**16.1 Does hand-written assembly still beat compilers?** *For*: in narrow kernels —
crypto, codecs, string/parsing primitives — with a knowledgeable author on a known
microarchitecture, yes, and measurably. *Against*: the gap closed enormously, compilers
retarget for free, and most claimed wins evaporate under proper benchmarking or on the
next CPU generation. **The synthesis practitioners actually apply: intrinsics for almost
everything, assembly for the last few percent on the few kernels that justify permanent
maintenance.**

**16.2 CISC vs. RISC.** Largely a resolved non-question — both decode to internal µops and
the ISA-level distinction matters far less than it did. What survives is real: **decode
complexity and code density** (x86 pays for the first, gains on the second), and the
argument that a clean ISA is cheaper to implement and verify.

**16.3 Fixed-width SIMD vs. scalable vectors.** *For scalable*: one binary across vector
widths, no epilogue, future-proof. *Against*: harder to reason about, harder to
hand-schedule, less mature tooling, and you can't see the register width you're working
with. The industry is split — x86 doubled down on fixed-width with AVX10, while ARM and
RISC-V both chose scalable.

**16.4 AVX-512's ISA design.** *For*: mask registers and 32 registers are genuinely
excellent, and it's the most capable SIMD ISA. *Against*: Linus Torvalds' well-known
criticism — fragmentation, downclocking, and die area spent on benchmarks rather than real
code. **AVX10 is Intel conceding the fragmentation half of that argument.**

**16.5 Should you learn assembly at all?** *For*: it's the only way to understand what your
machine and your compiler actually do, and it's indispensable for debugging optimized code,
security work, and systems programming. *Against*: as a *writing* skill it's applicable to
a shrinking share of work. **The consensus is to learn to read fluently and write rarely.**

**16.6 Which ISA to learn first.** **RISC-V** is the best-designed teaching target and the
easiest to hold in your head. **AArch64** is the best balance of clean design and real-world
ubiquity. **x86-64** is the ugliest and the one whose disassembly you're most likely to have
to read. Learning any one makes the next much easier.

---
