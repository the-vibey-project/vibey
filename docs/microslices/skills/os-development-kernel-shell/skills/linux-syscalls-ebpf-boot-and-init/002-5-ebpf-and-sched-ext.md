---
id: skill-5-ebpf-and-sched-ext-770664002c
purpose: 5 ebpf and sched ext
source: src/vibey_tools/skills/plugins/os-development-kernel-shell/skills/linux-syscalls-ebpf-boot-and-init/SKILL.md
requires: ["skill-4-syscalls-and-the-userspace-abi-614d890180"]
links: ["skill-6-boot-8ee5a95db5"]
---

## §5. eBPF and sched_ext

### 5.1 What eBPF actually is

A **verified, JIT-compiled, sandboxed in-kernel VM.** You compile restricted C (or Rust)
to BPF bytecode, the kernel's **verifier** proves it terminates and accesses only memory
it's allowed to, and it's JITed to native code and attached to a hook.

**The verifier's guarantees** [DURABLE]: it does a DAG check to reject loops and
unreachable code (bounded loops are allowed in modern kernels), then symbolically
executes every path tracking register types and value ranges. It rejects reads of
uninitialized registers, out-of-bounds access, invalid pointer arithmetic, and unbounded
loops. **This is what makes it safe to let unprivileged-ish code run in ring 0.**

**Attach points**: kprobes/kretprobes, fentry/fexit (BTF-based, cheaper), tracepoints,
USDT, perf events, LSM hooks (**BPF-LSM**), XDP (at the driver, before `skb` allocation —
the fastest packet path in Linux), tc/clsact, cgroup hooks, socket ops, and
**struct_ops** (implementing a kernel interface in BPF — used for TCP congestion control,
HID drivers, and schedulers).

**Key infrastructure**: **BTF** (BPF Type Format — kernel type info, requires
`CONFIG_DEBUG_INFO_BTF=y`), **CO-RE** (Compile Once, Run Everywhere — relocations against
the running kernel's BTF, which is what makes portable BPF binaries possible), maps
(hash, array, ringbuf, per-CPU, LRU), `libbpf`, `bpftool`, and the higher-level
`bpftrace`, `bcc`, and Rust's `aya`.

```c
// A minimal CO-RE tracing program (libbpf skeleton style)
#include <vmlinux.h>
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_tracing.h>

struct { __uint(type, BPF_MAP_TYPE_RINGBUF); __uint(max_entries, 256*1024); } rb SEC(".maps");

SEC("fentry/do_unlinkat")           // fentry: cheaper than kprobe, needs BTF
int BPF_PROG(on_unlink, int dfd, struct filename *name)
{
        struct event *e = bpf_ringbuf_reserve(&rb, sizeof(*e), 0);
        if (!e) return 0;                                  // ALWAYS check
        e->pid = bpf_get_current_pid_tgid() >> 32;
        bpf_probe_read_kernel_str(&e->file, sizeof(e->file), name->name);
        bpf_ringbuf_submit(e, 0);
        return 0;
}
char LICENSE[] SEC("license") = "GPL";   // required for most helpers
```

> **⚠️ GOTCHA — "the verifier rejected my program" is the whole BPF learning curve.**
> Common causes: an unchecked pointer (every map lookup can return NULL), a loop the
> verifier can't bound, exceeding the instruction/complexity limit, reading kernel memory
> without `bpf_probe_read_kernel`, or a helper not allowed in that program type. Read the
> verifier log from the *bottom* — the last lines are usually the real problem.

### 5.2 sched_ext — writing a CPU scheduler in BPF

**[VERSIONED] Merged in Linux 6.12.** `sched_ext` is a scheduling class that delegates
policy to a BPF program via `struct_ops`, letting you **load and hot-swap a CPU scheduler
at runtime without rebooting**. This is a genuinely significant change: scheduler
experimentation used to require a kernel patch, a build, and a reboot.

Concepts: **DSQs** (dispatch queues) mediate tasks between core kernel and the BPF
scheduler; callbacks include `select_cpu`, `enqueue`, `dispatch`, `running`, `stopping`.
**Safety mechanisms are the point**: if the BPF scheduler errors, stalls a runnable task,
or you hit SysRq-S, **the kernel aborts it and reverts every task to the fair class**.
`SCX_OPS_SWITCH_PARTIAL` lets only `SCHED_EXT` tasks use it while everything else stays
on EEVDF.

Required config: `CONFIG_BPF=y CONFIG_SCHED_CLASS_EXT=y CONFIG_BPF_SYSCALL=y
CONFIG_BPF_JIT=y CONFIG_DEBUG_INFO_BTF=y`. **`CONFIG_DEBUG_INFO_BTF` matters more than it
looks** — without BTF, CO-RE relocations can't resolve and every BPF scheduler fails to
load with an unhelpful "relocation failed."

The `scx` project ships real schedulers: `scx_simple`, `scx_rusty` (hybrid Rust userspace
+ BPF hot path), `scx_lavd` (latency-aware, gaming), `scx_bpfland`, `scx_layered` (match
tasks into layers by name/cgroup/nice and give each layer a policy). **Meta has deployed
sched_ext schedulers in production for web workloads.**

Distro status (2026): Fedora, Arch, CachyOS, NixOS unstable, and openSUSE Tumbleweed ship
SCX-enabled kernels; Ubuntu 26.04 LTS has it in the HWE kernel but not GA; Debian stable
needs backports or a self-build. Check with `cat /sys/kernel/sched_ext/state` and
`/sys/kernel/sched_ext/root/ops`.

---
