---
id: skill-8-reading-disassembly-d0b146299d
purpose: 8 reading disassembly
source: src/vibey_tools/skills/plugins/assembly-programming/skills/assembly-toolchain-performance-and-simd/SKILL.md
requires: ["skill-7-assemblers-and-toolchain-ac83728c71"]
links: ["skill-9-performance-9943efcadf"]
---

## §8. Reading Disassembly

**[DURABLE] This is the highest-value assembly skill, and most people who "know assembly"
mean this.**

### 8.1 The workflow

1. **Compiler Explorer (godbolt.org)** — paste source, pick a compiler and flags, watch the
   assembly change. Colour-coded source↔asm mapping. **If you want to learn assembly in
   2026, this is where you do it.**
2. `gcc -S -O2 -masm=intel -fverbose-asm` for local work.
3. `objdump -d --no-show-raw-insn -M intel binary` for shipped binaries.
4. `perf annotate` to see assembly with sample counts attached — *this* is how you find the
   hot instruction.

### 8.2 Recognizing patterns

```asm
; array indexing: a[i] where a is int32*
mov  eax, [rdi + rsi*4]

; a loop the compiler unrolled and vectorized (the give-away is the wide moves)
.L4:
  movdqu xmm0, [rdi + rax]
  paddd  xmm0, xmm1
  movdqu [rdi + rax], xmm0
  add    rax, 16
  cmp    rax, rdx
  jne    .L4

; a switch compiled to a jump table
  cmp   edi, 5
  ja    .Ldefault
  jmp   [.Ltable + rdi*8]

; a division by a constant, strength-reduced to multiply-and-shift
  mov   rax, 0x5555555555555556   ; magic number for /3
  imul  rdx
  ...

; a tail call (jmp, not call — no new stack frame)
  jmp   other_function
```

**[DURABLE] What surprises people reading `-O2` output for the first time:** variables
don't exist (they're in registers, or gone), the source line order is scrambled, functions
have been inlined away, loops are unrolled and vectorized, dead code is deleted entirely,
and **the debugger's line numbers are approximate at best**. This is normal and correct —
it is also why "it works in debug, fails in release" is usually a latent bug (UB) rather
than a compiler bug.

---
