---
id: skill-4-syscalls-and-the-userspace-abi-614d890180
purpose: 4 syscalls and the userspace abi
source: src/vibey_tools/skills/plugins/os-development-kernel-shell/skills/linux-syscalls-ebpf-boot-and-init/SKILL.md
requires: []
links: ["skill-5-ebpf-and-sched-ext-770664002c"]
---

## §4. Syscalls and the Userspace ABI

### 4.1 "We do not break userspace"

**[DURABLE — the kernel's foundational social contract.]** If a change makes a working
userspace program stop working, it is a kernel regression and gets reverted, regardless
of whether the program was relying on documented behaviour. Linus enforces this
personally and the mailing-list archives are full of it.

Practical consequences:
- Syscall numbers and semantics are permanent.
- `struct` layouts in `include/uapi/` are permanent. **Extend with padding fields and a
  size/flags field designed in from the start** — the modern pattern
  (`sched_setattr`, `openat2`, `clone3`, `bpf`) passes a struct plus its size so the
  kernel can distinguish old callers from new.
- New functionality goes in new syscalls or new flags, not changed behaviour.
- `/sys` and `/proc` output formats are ABI once shipped. Adding a column to a
  space-separated file breaks parsers and has caused real reverts.

### 4.2 Mechanics

```
userspace → libc wrapper → syscall instruction (x86-64: `syscall`, arm64: `svc`)
  → arch entry (arch/x86/entry/) → sys_call_table → SYSCALL_DEFINEn(name, ...)
    → work → return negative errno on failure
      → libc sets errno = -ret, returns -1
```
- **vDSO** (`linux-vdso.so.1`) is a small shared object the kernel maps into every
  process so hot, harmless calls (`clock_gettime`, `gettimeofday`, `getcpu`) can be
  serviced **without a syscall at all**. If you're wondering why `clock_gettime` costs
  ~20 ns, this is why.
- `SYSCALL_DEFINE`, `__user` annotations, `copy_from_user`/`copy_to_user` (which can
  fault and therefore can sleep — never under a spinlock), and `access_ok()`.

> **⚠️ GOTCHA — TOCTOU on userspace memory.** Never read a userspace value twice and
> assume it's the same. Copy it into kernel memory once, validate the copy, and use the
> copy. Userspace can change it between your check and your use — this is a classic
> privilege-escalation pattern.

### 4.3 io_uring — the modern async I/O interface, and its reputation

`io_uring` (kernel 5.1+, Jens Axboe) uses shared submission and completion ring buffers
so batches of I/O can be submitted and reaped **without syscalls per operation**. It is
genuinely fast and now underpins high-performance storage and networking userspace.

**It is also the kernel's most notorious recent attack surface.** Google reported that
**~60% of kernel exploit submissions to its VRP in one period targeted io_uring**, paying
out roughly **$1M** in io_uring bounties out of ~$1.8M total for kernel exploits.
Consequences: Google **disabled io_uring in ChromeOS**, restricted it on Android via
seccomp-bpf and SELinux, and containerd's default seccomp profile disallows io_uring
syscalls. A published proof-of-concept **rootkit performs all its operations through
io_uring specifically to evade syscall-based monitoring** — which is the structural
problem: **you cannot write fine-grained seccomp filters for io_uring**, because the
actual operations are opaque to BPF at the syscall boundary. It's effectively all-or-
nothing.

**Practical control:** `sysctl kernel.io_uring_disabled=2` disables it entirely
(`=1` restricts to a group). The trade-off is real — some PostgreSQL-style I/O-heavy
benchmarks claim 2–3× gains. **Decide from a threat model, not a benchmark or a
headline.**

---
