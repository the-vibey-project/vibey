---
id: skill-1-the-machine-model-43bdcbc0f5
purpose: 1 the machine model
source: src/vibey_tools/skills/plugins/assembly-programming/skills/assembly-fundamentals-and-isas/SKILL.md
requires: ["skill-0-routing-6231e1d3de"]
links: ["skill-2-x86-64-06d11e576f"]
---

## §1. The Machine Model

### 1.1 What's actually there

```
┌──────────────────────────────────────────────────────────────┐
│ ARCHITECTURAL STATE (what the ISA promises)                  │
│   general-purpose registers · SIMD/vector registers          │
│   program counter · flags/condition codes · stack pointer    │
│   control/system registers · memory (virtual address space)  │
└──────────────────────────────────────────────────────────────┘
                    ↕  (the ISA is a CONTRACT, not a description)
┌──────────────────────────────────────────────────────────────┐
│ MICROARCHITECTURE (what actually happens)                    │
│   fetch → decode → µop cache → RENAME (physical regs ≫ arch) │
│   → scheduler/reservation stations → OUT-OF-ORDER EXECUTION  │
│   across multiple ports → load/store buffers → RETIRE in     │
│   order · branch predictors · L1/L2/L3 caches · TLBs ·       │
│   prefetchers · store-to-load forwarding · speculation       │
└──────────────────────────────────────────────────────────────┘
```

**[DURABLE] Register renaming is why most naive assembly intuitions fail.** The CPU has
far more physical registers than architectural ones and renames on the fly, so
**write-after-write and write-after-read "dependencies" are free** — only true
read-after-write data dependencies cost you. This is why `xor eax, eax` is faster than
`mov eax, 0` (it's recognized as a zeroing idiom and breaks the dependency chain), and why
"reusing a register to save registers" can be actively harmful.

**[DURABLE] The three things that actually determine speed** (§9 → `assembly-toolchain-performance-and-simd`): the **critical path
through the dependency graph**, **memory access patterns**, and **branch predictability**.
Instruction *count* is a distant fourth and is the thing beginners optimize.

### 1.2 Registers

| Class | Purpose |
|---|---|
| General-purpose | Integers, addresses. x86-64: 16 (32 with APX); AArch64: 31 + zero register; RISC-V: 32 (x0 hardwired to zero) |
| SIMD/vector | Packed data. §10 → `assembly-toolchain-performance-and-simd` |
| Floating-point | Separate on some ISAs, shared with SIMD on others |
| Flags/condition | x86 EFLAGS, ARM NZCV. **RISC-V has none** — a deliberate design choice |
| Special | PC/IP, SP, link register, TLS base, system/control registers |

**[DURABLE] A zero register is a surprisingly large ISA win.** AArch64's `xzr`/`wzr` and
RISC-V's `x0` let one instruction encoding serve many purposes: `add rd, rs, x0` is a move,
`beq rs, x0, label` is branch-if-zero, storing `xzr` is a memset. x86 has no zero register
and needs distinct encodings for all of it.

### 1.3 Addressing modes

```
x86-64:   [base + index*scale + disp]        scale ∈ {1,2,4,8}   — very expressive
          mov rax, [rbx + rcx*8 + 16]
AArch64:  [base], [base, #imm], [base, Xn{, LSL #s}], pre/post-index
          ldr x0, [x1, #16]!        pre-index:  x1 += 16, then load
          ldr x0, [x1], #16         post-index: load, then x1 += 16
RISC-V:   [base + imm12]  ONLY                                   — deliberately minimal
          ld  a0, 16(a1)
```
**[DURABLE] This is the clearest illustration of the CISC/RISC trade-off that survives
into 2026.** x86's addressing modes fold address arithmetic into the load for free —
but they're one reason x86 decoding is hard. RISC-V's single mode means indexed access
costs an extra `add`, which the designers judged a fair price for decode simplicity.
Neither is wrong; they optimize different things.

### 1.4 Endianness, alignment, and memory ordering

- **Endianness**: x86-64, AArch64 (in practice), and RISC-V are all **little-endian**
  today. Big-endian survives in network byte order, some MIPS/PowerPC/SPARC deployments,
  and file formats. **Byte-swap instructions exist**: `bswap`/`movbe` (x86), `rev` (ARM),
  `rev8` (RISC-V Zbb).
- **Alignment**: x86-64 tolerates unaligned scalar access with a small penalty (and
  *requires* alignment for some SIMD instructions and all atomics that must not split a
  cache line). ARM and RISC-V vary — unaligned may fault, may trap-and-emulate slowly, or
  may work fine. **⚠️ A split-cache-line access is dramatically slower everywhere, and a
  split-page access worse still.**
- **Memory ordering [DURABLE, and the most dangerous area in multicore assembly]:**

| ISA | Model |
|---|---|
| **x86-64** | **TSO** (total store order) — strong. Only store→load can reorder. `mfence`/`lock`-prefixed ops for the rest |
| **AArch64** | **Weak**, with acquire/release built into instructions: `ldar`/`stlr`, plus `dmb`/`dsb`/`isb` barriers |
| **RISC-V** | **Weak** (RVWMO), with `fence` and `.aq`/`.rl` suffixes on atomics |
| **POWER** | Weak, notoriously so |

> **⚠️ GOTCHA — x86's strong ordering hides bugs that ARM and RISC-V expose.** Concurrent
> code developed and tested only on x86 routinely breaks on AArch64, because the missing
> barrier never mattered before. This is one of the most common real-world porting
> failures, and it produces rare, load-dependent corruption rather than a clean crash.

---
