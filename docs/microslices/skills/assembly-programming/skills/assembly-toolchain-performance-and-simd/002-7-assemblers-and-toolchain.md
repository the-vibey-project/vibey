---
id: skill-7-assemblers-and-toolchain-ac83728c71
purpose: 7 assemblers and toolchain
source: src/vibey_tools/skills/plugins/assembly-programming/skills/assembly-toolchain-performance-and-simd/SKILL.md
requires: ["skill-6-calling-conventions-and-abis-8daa8eea89"]
links: ["skill-8-reading-disassembly-d0b146299d"]
---

## §7. Assemblers and Toolchain

### 7.1 The syntax split

**[DURABLE] Two syntaxes for x86, and the operand order is reversed.** This causes more
confusion than any other single thing in x86 assembly.

```asm
; Intel syntax (NASM, MASM, and `objdump -M intel`)     DEST, SRC
mov  rax, rbx
mov  rax, [rbx + rcx*8 + 16]
add  rax, 1

# AT&T / GAS syntax (default GNU)                        SRC, DEST
movq %rbx, %rax
movq 16(%rbx,%rcx,8), %rax
addq $1, %rax          # % on registers, $ on immediates, suffix for size
```
AArch64 and RISC-V have only one syntax each, which is one of several reasons they're
pleasanter to learn.

### 7.2 The tools

| Tool | Use |
|---|---|
| **GAS** (`as`, via `gcc`/`clang`) | The default on Unix. AT&T by default; `.intel_syntax noprefix` available |
| **NASM** / **YASM** | Intel syntax, standalone, excellent macro system. The x86 favourite |
| **Clang's integrated assembler** | Now the default in the LLVM toolchain; handles both syntaxes |
| **MASM** (`ml64`) | Windows/MSVC |
| **`objdump -d`**, **`llvm-objdump`** | Disassembly |
| **Ghidra**, **IDA Pro**, **Binary Ninja**, **radare2/rizin** | Reverse engineering with decompilation |
| **Compiler Explorer (godbolt.org)** | **The single most valuable tool in this whole document.** See §8 |
| **`perf`**, **VTune**, **uProf**, **Instruments** | Profiling with hardware counters |
| **LLVM-MCA**, **uiCA**, **OSACA** | Static throughput/latency analysis of a loop |
| **`gdb`/`lldb`** | `layout asm`, `si`, `info registers`, `x/i $pc` |

**Directives you need**: `.text`/`.data`/`.bss`/`.rodata`, `.global`, `.align`/`.p2align`,
`.byte`/`.word`/`.quad`, `.asciz`, `.type`/`.size` (**required for correct ELF symbols and
for the profiler to attribute samples**), and **CFI directives** (`.cfi_startproc`,
`.cfi_def_cfa_offset`, `.cfi_offset`, `.cfi_endproc`).

> **⚠️ GOTCHA — omit CFI and your function becomes invisible to unwinding.** Backtraces
> stop at your function, C++ exceptions cannot propagate through it, and profilers
> mis-attribute its samples. Hand-written assembly without CFI is a debugging black hole,
> and it's the most commonly skipped step.
CHUNKEOF
echo ok; wc -l /home/claude/assembly-programming.md 2>/dev/null || true

---
