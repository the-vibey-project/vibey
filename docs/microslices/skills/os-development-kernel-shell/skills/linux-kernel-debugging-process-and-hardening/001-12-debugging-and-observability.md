---
id: skill-12-debugging-and-observability-65da5206a8
purpose: 12 debugging and observability
source: src/vibey_tools/skills/plugins/os-development-kernel-shell/skills/linux-kernel-debugging-process-and-hardening/SKILL.md
requires: []
links: ["skill-13-the-kernel-development-process-bdd52622a5"]
---

## §12. Debugging and Observability

### 12.1 The kernel debug configs to build with

**[DURABLE] Turn these on in development. Every one of them turns a heisenbug into a
reproducible splat:**
```
CONFIG_DEBUG_KERNEL=y
CONFIG_DEBUG_INFO=y CONFIG_DEBUG_INFO_BTF=y     # BTF also required for CO-RE BPF
CONFIG_KASAN=y                                   # use-after-free, OOB. ~2-3x slowdown
CONFIG_UBSAN=y                                   # undefined behaviour
CONFIG_KCSAN=y                                   # data races
CONFIG_PROVE_LOCKING=y                           # lockdep — deadlock detection
CONFIG_DEBUG_ATOMIC_SLEEP=y                      # sleeping in atomic context
CONFIG_PROVE_RCU=y
CONFIG_DEBUG_OBJECTS=y
CONFIG_SLUB_DEBUG_ON=y                           # redzoning, poisoning
CONFIG_DEBUG_PAGEALLOC=y
CONFIG_FAULT_INJECTION=y                         # make allocations fail on purpose
CONFIG_KFENCE=y                                  # low-overhead; safe for PRODUCTION
```
**KASAN + lockdep together find the overwhelming majority of new kernel bugs before they
reach anyone else.** KFENCE is the one you can leave on in production (sampling-based,
near-zero overhead).

### 12.2 Reading an oops

```
BUG: kernel NULL pointer dereference, address: 0000000000000010
#PF: supervisor read access in kernel mode
Oops: 0000 [#1] PREEMPT SMP NOPTI
CPU: 3 PID: 1234 Comm: myapp Tainted: G           O       6.18.40 #1
RIP: 0010:foo_read+0x42/0x180 [mymod]     ← WHERE. function+offset/size [module]
...
Call Trace:
 <TASK>
 vfs_read+0xb4/0x330
 ksys_read+0x6b/0xf0
 do_syscall_64+0x5c/0x90
```
Read it in this order:
1. **The first line** — what kind of fault, and the bad address. `0x10` means a NULL
   pointer plus a small struct offset; `0x6b6b6b6b...` is SLUB poison (use-after-free);
   `0xffffffffffffffff` is often an unchecked `ERR_PTR`.
2. **`RIP: function+offset/size`** — the exact instruction. Resolve with
   `./scripts/faddr2line vmlinux foo_read+0x42/0x180` or `addr2line`.
3. **`Tainted:`** — `G` clean-ish, `O` out-of-tree module loaded, `P` proprietary,
   `D` previous oops, `W` previous warning. **Maintainers will ask about taint first.**
4. **Call trace** — the path in. Entries with `?` are stale stack values, not real frames.
5. **`[#1]`** — first oops. A second one after the first is usually corruption from the
   first; only the first is trustworthy.

`decode_stacktrace.sh` symbolizes the whole thing. `panic_on_oops=1` and `kdump`/`crash`
give you a full vmcore for post-mortem analysis with `crash` or `drgn`.

### 12.3 Tracing — the hierarchy

| Tool | Overhead | Use for |
|---|---|---|
| `printk`/`pr_debug` + **dynamic debug** | high if hot | Coarse. `echo 'file foo.c +p' > /sys/kernel/debug/dynamic_debug/control` |
| **ftrace** (`/sys/kernel/tracing`) | low | Function graph tracing, latency tracers, per-event tracepoints. Built in, no tooling needed |
| **`trace-cmd` / KernelShark** | low | ftrace with a usable interface |
| **perf** | low-medium | CPU profiling, `perf record/report`, `perf top`, `perf trace`, hardware counters, **flame graphs** |
| **bpftrace** | low | One-liners with real logic. The modern first reach |
| **BCC / libbpf tools** | low | Prewritten: `execsnoop`, `opensnoop`, `biolatency`, `tcpconnect`, `runqlat`, `offcputime` |
| **LTTng** | low | High-volume production tracing with a stable format |
| **`strace` / `ltrace`** | **very high** | Userspace syscall/library tracing. ptrace-based — do not use on a hot production process |
| **KGDB / KDB** | — | Interactive source-level kernel debugging (needs a serial console or VM) |
| **QEMU + gdb** | — | **The best kernel development loop.** `qemu -s -S` then `gdb vmlinux` |

```bash
# The five bpftrace one-liners worth memorizing
bpftrace -e 'tracepoint:syscalls:sys_enter_openat { @[comm] = count(); }'
bpftrace -e 'kprobe:vfs_read { @bytes = hist(arg2); }'
bpftrace -e 'tracepoint:sched:sched_process_exec { printf("%s %s\n", comm, str(args->filename)); }'
bpftrace -e 'kretprobe:do_sys_openat2 /retval < 0/ { @errs[comm, -retval] = count(); }'
bpftrace -e 'profile:hz:99 { @[kstack] = count(); }'      # sampled kernel stacks

# ftrace without any tooling
cd /sys/kernel/tracing
echo function_graph > current_tracer && echo do_sys_openat2 > set_graph_function
echo 1 > tracing_on; cat trace_pipe

# perf → flame graph
perf record -F 99 -a -g -- sleep 30 && perf script | stackcollapse-perf.pl | flamegraph.pl > fg.svg
```

### 12.4 Testing

`kunit` (in-kernel unit tests, run under UML or QEMU), `kselftest`
(`tools/testing/selftests`), **syzkaller** (coverage-guided syscall fuzzer — the single
largest source of kernel bug reports in existence), `xfstests` for filesystems, LTP.
**Send a syzkaller reproducer with your bug report and you will get a fix; send a
description and you may not.**

---
