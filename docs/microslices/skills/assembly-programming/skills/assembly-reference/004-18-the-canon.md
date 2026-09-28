---
id: skill-18-the-canon-92b270feaa
purpose: 18 the canon
source: src/vibey_tools/skills/plugins/assembly-programming/skills/assembly-reference/SKILL.md
requires: ["skill-17-currency-snapshot-verified-august-2026-ae617ba534"]
links: ["skill-19-quick-reference-216f2446b3"]
---

## §18. The Canon

### 18.1 The vendor manuals — and here they genuinely are the field

- **Intel® 64 and IA-32 Architectures Software Developer's Manuals** — Volume 2 is the
  instruction reference; Volume 3 is systems programming. Also the **Optimization Reference
  Manual** and the **Instruction Set Extensions and Future Features** manual (where APX and
  AVX10 live).
- **AMD64 Architecture Programmer's Manual** + the **Software Optimization Guide** per
  family. **Read both vendors' manuals** — they differ on details that matter.
- **Arm Architecture Reference Manual (Arm ARM)** for A-profile, and the **Software
  Optimization Guides** per core (Neoverse, Cortex-X/A). Arm's **Developer** site and the
  **Learn the Architecture** series are unusually good.
- **RISC-V ISA specifications** (unprivileged and privileged) and the **Ratified
  Specifications Library** at `docs.riscv.org`, plus **riscv/riscv-profiles** on GitHub for
  RVA23.
- **System V ABI: AMD64 Architecture Processor Supplement**, **AAPCS64**, and the
  **RISC-V psABI** — the calling-convention documents in §6 → `assembly-toolchain-performance-and-simd`.

### 18.2 The performance references

- **Agner Fog's manuals** (`agner.org/optimize`) — five volumes, free, and the
  **instruction tables** are the canonical latency/throughput/port reference for every x86
  microarchitecture. **If you optimize x86, this is not optional.**
- **uops.info** — automated, exhaustive, machine-measured instruction data.
- **Intel intrinsics guide** (`intel.com/content/www/us/en/docs/intrinsics-guide`) and
  **Arm's Neon/SVE intrinsics references**.
- **Brendan Gregg**, *Systems Performance* — for the layer above.
- **Ulrich Drepper**, "What Every Programmer Should Know About Memory" — dated in specifics,
  still the best explanation of why §9.3 → `assembly-toolchain-performance-and-simd` is the section that matters.

### 18.3 Books

| Author | Work | Why |
|---|---|---|
| **Bryant & O'Hallaron** | ***Computer Systems: A Programmer's Perspective*** (CS:APP) | **The best book for learning assembly in context.** Teaches x86-64 as part of understanding the whole machine |
| **Patterson & Hennessy** | *Computer Organization and Design* (**RISC-V edition**) | The undergraduate standard, now RISC-V-based |
| **Hennessy & Patterson** | *Computer Architecture: A Quantitative Approach* | The graduate one — why microarchitecture is what it is |
| **Randall Hyde** | *The Art of Assembly Language* | Comprehensive, opinionated, good on fundamentals |
| **Daniel Kusswurm** | *Modern X86 Assembly Language Programming*; *Modern Arm Assembly* | The most current practical SIMD-focused books |
| **Ray Seyfarth** | *Introduction to 64 Bit Assembly Programming* | Clean, modern, Linux-focused |
| **Pyeatt & Ughetta** | *ARM 64-Bit Assembly Language* | Solid AArch64 treatment |
| **Waterman & Asanović** | *The RISC-V Reader* | Short, excellent, by the architects |
| **Eldad Eilam** | *Reversing: Secrets of Reverse Engineering* | The reading-assembly discipline |
| **Dennis Andriesse** | *Practical Binary Analysis* | Modern, tool-focused |
| **Chris Kaspersky** | *Code Optimization: Effective Memory Usage* | Dated but instructive |
| **Warren** | ***Hacker's Delight*** | Bit-twiddling algorithms — the raw material of good assembly |
| **Abrash** | *Graphics Programming Black Book* | Historically important, and the best writing about the *craft* of optimization ever published. **Read it for the method, not the numbers** |

### 18.4 Online and people
**Compiler Explorer** (godbolt.org — Matt Godbolt) is the single best tool; his talks on
"what has my compiler done for me lately" are the best introduction to reading assembly.
**Agner Fog**, **Daniel Lemire** (SIMD parsing, `simdjson`), **Wojciech Muła**
(`0x80.pl` — SIMD algorithms), **Travis Downs** (performance archaeology),
**Peter Cordes** (his Stack Overflow x86 answers are a reference work in their own right,
and the **x86 tag wiki** he maintains is genuinely excellent), **Fabian Giesen** (`ryg`),
**Anger's forum**, **stuffedcow.net** (Henry Wong, branch prediction), and the
**highload.fun** / **Algorithmica** (`en.algorithmica.org/hpc`) performance material.

---
