---
id: skill-11-systems-assembly-f80b040c87
purpose: 11 systems assembly
source: src/vibey_tools/skills/plugins/assembly-programming/skills/assembly-systems-crypto-and-inline/SKILL.md
requires: []
links: ["skill-12-cryptographic-and-constant-time-assembly-d972d30722"]
---

## §11. Systems Assembly

**[DURABLE] Some things simply cannot be written in a high-level language**, and this is
where assembly is unavoidable rather than merely faster:

- **Reset/boot code** — before the stack, the data section, or any C runtime exists.
- **Interrupt and exception vectors** — save volatile state, switch stacks, call the
  handler, restore precisely, return with the special instruction (`iret`, `eret`, `mret`).
- **Context switching** — save one thread's callee-saved registers and stack pointer,
  load another's. Fundamentally unexpressible in C.
- **Syscall entry/exit stubs**.
- **`setjmp`/`longjmp`, coroutines, stack switching, unwinding**.
- **Atomics and lock primitives** where you need exact instruction selection.
- **Self-modifying code, JIT emission, trampolines, PLT stubs**.
- **Cache and TLB maintenance** (`clflush`, `wbinvd`, `dc civac`, `tlbi`, `sfence.vma`) and
  memory barriers.

```asm
; Linux x86-64 syscall  (write(1, msg, len))
mov rax, 1          ; syscall number
mov rdi, 1          ; fd
mov rsi, msg
mov rdx, len
syscall             ; ⚠️ CLOBBERS rcx and r11 — the ABI differs from a function call
```
> **⚠️ GOTCHA — the syscall ABI is not the function-call ABI.** On x86-64 Linux, the
> **4th argument is `r10`, not `rcx`** (because `syscall` destroys `rcx`), and `rcx` and
> `r11` are clobbered. On AArch64 the number goes in `x8` and the instruction is `svc #0`.
> Getting this wrong produces bafflingly wrong syscall behaviour.

**JIT-specific concerns**: **W^X** (never map memory writable and executable
simultaneously — use dual mapping or `mprotect` transitions; **macOS on Apple Silicon
requires `pthread_jit_write_protect_np`**), and **instruction-cache invalidation** — on
ARM and RISC-V, writing bytes is not enough; you must flush D-cache to the point of unity
and invalidate I-cache (`dc cvau` / `ic ivau` / `isb`, or `fence.i`). **x86 has coherent
I-cache and doesn't need this**, which is exactly why JIT code that works on x86 breaks
mysteriously when ported.

---
