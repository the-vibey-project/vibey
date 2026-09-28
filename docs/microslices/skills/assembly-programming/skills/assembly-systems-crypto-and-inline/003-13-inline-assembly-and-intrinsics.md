---
id: skill-13-inline-assembly-and-intrinsics-ead05708cd
purpose: 13 inline assembly and intrinsics
source: src/vibey_tools/skills/plugins/assembly-programming/skills/assembly-systems-crypto-and-inline/SKILL.md
requires: ["skill-12-cryptographic-and-constant-time-assembly-d972d30722"]
links: ["skill-14-debugging-testing-and-verification-c04e45f162"]
---

## §13. Inline Assembly and Intrinsics

### 13.1 Prefer intrinsics

**[DURABLE]** Intrinsics give you the specific instruction while keeping register
allocation, scheduling, inlining, and constant propagation. Inline assembly gives up all
of that and requires you to describe your effects to the compiler correctly — which is
where the bugs are.

### 13.2 GCC/Clang extended asm, and how to get it right

```c
__asm__ volatile (
    "addq %[b], %[a]"          // template
    : [a] "+r" (x)             // outputs:  "+" = read-write
    : [b] "r"  (y)             // inputs
    : "cc", "memory"           // CLOBBERS — the part people get wrong
);
```
**The constraint letters that matter**: `r` (any GPR), `m` (memory), `i` (immediate),
`=` (write-only output), `+` (read-write), `&` (**early-clobber** — written before all
inputs are consumed).

> **⚠️ GOTCHA — the four inline-asm failure modes, in order of how much time they waste:**
> 1. **Missing `"memory"` clobber** when the asm reads or writes memory the compiler
>    thinks it knows about → the compiler caches a stale value in a register, and the bug
>    appears only at `-O2`.
> 2. **Missing `"cc"` clobber** when you modify flags → the compiler reuses flags it
>    thought were still valid.
> 3. **Missing `&` early-clobber** → the compiler assigns an output and an input to the
>    same register, and your asm overwrites the input before reading it.
> 4. **Missing `volatile`** on asm with side effects but no used output → the compiler
>    deletes it, or hoists it out of a loop.
>
> All four produce code that works at `-O0` and fails at `-O2`, which is the worst
> possible debugging experience.

**MSVC has no inline assembly for x64** — you use intrinsics or a separate `.asm` file
assembled by MASM. This is a real portability constraint on cross-platform projects.

**Naked functions / separate `.s` files** are cleaner than large inline blocks: you get
full control, real assembler syntax, proper CFI, and the code is testable and profilable.

---
