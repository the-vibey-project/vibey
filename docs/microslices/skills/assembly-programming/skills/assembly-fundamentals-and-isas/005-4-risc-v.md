---
id: skill-4-risc-v-158f761c5f
purpose: 4 risc v
source: src/vibey_tools/skills/plugins/assembly-programming/skills/assembly-fundamentals-and-isas/SKILL.md
requires: ["skill-3-aarch64-arm64-637d2f7098"]
links: ["skill-5-other-isas-worth-knowing-4a37752128"]
---

## §4. RISC-V

### 4.1 The design philosophy, and why it matters to you

**[DURABLE] RISC-V is a small base plus modular extensions**, which makes it the easiest
major ISA to learn and the most annoying to target portably.

```
RV32I / RV64I   base integer (I = 32 registers; E = 16, for embedded)
M  multiply/divide      A  atomics          F/D/Q  float (single/double/quad)
C  compressed (16-bit)  V  vector (§10)     B  bit manipulation (Zba/Zbb/Zbs)
Zicsr control regs      Zifencei            Zk*  scalar crypto     Zvk*  vector crypto
```
The shorthand: **RV64GC** = IMAFD + Zicsr + Zifencei + C, the general-purpose target.

```
x0/zero  hardwired zero     x1/ra  return address     x2/sp  stack pointer
x3/gp    global pointer     x4/tp  thread pointer     x5–7/t0–2  temporaries
x8/s0/fp saved / frame ptr  x9/s1  saved
x10–17/a0–a7  arguments and return values      x18–27/s2–11  saved
x28–31/t3–6   temporaries
```

**Notably absent: condition flags.** Comparison and branch are fused into one instruction
(`beq`, `bne`, `blt`, `bge`, `bltu`, `bgeu`), and `slt`/`sltu` materialize a comparison as
0/1. This removes a serialization point and a rename hazard that x86 and ARM both carry.

```asm
addi sp, sp, -16
sd   ra, 8(sp)
sd   s0, 0(sp)
# ...
ld   ra, 8(sp)
ld   s0, 0(sp)
addi sp, sp, 16
ret                  # pseudo-instruction for: jalr x0, 0(ra)
```

**⚠️ Pseudo-instructions are pervasive and you must know they're not real**: `li`, `la`,
`mv`, `nop`, `ret`, `call`, `j`, `beqz`, `not`, `neg`. The assembler expands each into one
or more real instructions, and `li` with a large constant becomes `lui`+`addi`.

### 4.2 Profiles — the fragmentation fix

**[VERSIONED]** The extension modularity created a real portability problem, and
**profiles** are the answer: a named set of mandatory and optional extensions that
software can target.

**RVA23 was ratified 21 October 2024** and is the current 64-bit application-processor
profile. What matters for assembly programmers:
- **The V (vector) extension is now MANDATORY** — it was optional in RVA22. Vectors are no
  longer an optional accelerator; they're a baseline capability software can assume.
- **RVA23 is the baseline requirement for the Android RISC-V ABI.**
- Also newly mandatory in RVA23U64: **Zvfhmin** (vector half-precision), **Zvbb** (vector
  bit manipulation), **Zvkt** (vector data-independent execution latency — see §12 → `assembly-systems-crypto-and-inline`),
  **Zihintntl**, **Zicond** (integer conditional ops), **Zimop**/**Zcmop**, **Zcb**,
  **Zfa**, and **Supm** (pointer masking).
- **The scalar crypto extensions Zkn and Zks are no longer options** — the stated goal is
  for hardware and software vendors to **move to vector crypto**, since vectors are now
  mandatory and vector crypto is substantially faster.
- The hypervisor extension is in the S-mode profile.
- Ratified specs are **frozen**: "No changes are allowed… Ratified extensions are never
  revised." Changes go into new extensions.

---
