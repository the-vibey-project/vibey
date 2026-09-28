---
id: skill-6-calling-conventions-and-abis-8daa8eea89
purpose: 6 calling conventions and abis
source: src/vibey_tools/skills/plugins/assembly-programming/skills/assembly-toolchain-performance-and-simd/SKILL.md
requires: []
links: ["skill-7-assemblers-and-toolchain-ac83728c71"]
---

## §6. Calling Conventions and ABIs

**[DURABLE] The ABI is the contract, and violating it produces bugs that appear far from
the cause.** You must know: which registers pass arguments, which are caller- vs.
callee-saved, where the return value goes, stack alignment, how structs are passed, and
how varargs work.

| | **System V AMD64** (Linux/macOS/BSD) | **Windows x64** | **AAPCS64** (ARM64) | **RISC-V** |
|---|---|---|---|---|
| Int args | rdi, rsi, rdx, rcx, r8, r9 | **rcx, rdx, r8, r9** only | x0–x7 | a0–a7 |
| FP args | xmm0–7 | xmm0–3 | v0–v7 | fa0–fa7 |
| Return | rax (rdx:rax for 128) | rax | x0 (x0,x1) | a0 (a0,a1) |
| Callee-saved | rbx, rbp, r12–r15 | rbx, rbp, rdi, rsi, r12–r15, **xmm6–15** | x19–x28, v8–v15 (**low 64 bits only**) | s0–s11, fs0–fs11 |
| Stack align at call | **16 bytes** | 16 bytes | **16 bytes** | 16 bytes |
| Special | **red zone: 128 bytes below rsp** usable without adjusting | **32-byte shadow space** the caller must allocate | x18 platform-reserved on some OSes | — |

> **⚠️ GOTCHA — the four ABI mistakes that account for most hand-written-assembly bugs:**
> 1. **Clobbering a callee-saved register** without saving it. The corruption surfaces in
>    the *caller*, arbitrarily later.
> 2. **Misaligning the stack.** SSE/NEON instructions fault or silently slow down, and
>    the failure appears inside an unrelated library function.
> 3. **Assuming System V on Windows** (or vice versa). Completely different argument
>    registers, plus Windows' shadow space and xmm6–15 preservation.
> 4. **AArch64 `v8–v15`: only the low 64 bits are callee-saved.** The upper halves are
>    caller-saved. This one bites SIMD code specifically.
>
> Also: the **red zone does not exist in kernel or interrupt context** (Linux compiles the
> kernel with `-mno-red-zone` for exactly this reason), and varargs on System V requires
> `al` to hold the number of vector registers used.

**Name mangling and symbol visibility**: C symbols may get a leading underscore (Darwin,
older platforms) and C++ names are mangled — use `extern "C"` and check with `nm`.

---
