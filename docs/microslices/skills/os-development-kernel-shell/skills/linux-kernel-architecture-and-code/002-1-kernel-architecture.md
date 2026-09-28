---
id: skill-1-kernel-architecture-23112f1bb4
purpose: 1 kernel architecture
source: src/vibey_tools/skills/plugins/os-development-kernel-shell/skills/linux-kernel-architecture-and-code/SKILL.md
requires: ["skill-0-routing-18ce400993"]
links: ["skill-2-writing-kernel-code-edeffd33b4"]
---

## §1. Kernel Architecture

### 1.1 The shape of it

```
┌───────────────────────────────────────────────────────────────┐
│ USERSPACE   applications · libc (glibc/musl) · systemd         │
└────────────────────────────┬──────────────────────────────────┘
                    syscalls │ vDSO │ /proc /sys /dev │ netlink │ BPF
┌────────────────────────────┴──────────────────────────────────┐
│ SYSTEM CALL INTERFACE                                          │
├──────────┬──────────┬──────────┬──────────┬───────────────────┤
│ Process  │ Memory   │ VFS      │ Network  │ Device drivers    │
│ sched,   │ mm, page │ fs, page │ netdev,  │ (60%+ of the      │
│ signals, │ alloc,   │ cache,   │ TCP/IP,  │  source tree)     │
│ futex,   │ slab,    │ block    │ netfilter│                   │
│ cgroups  │ swap     │ layer    │ XDP      │                   │
├──────────┴──────────┴──────────┴──────────┴───────────────────┤
│ CORE: locking · RCU · workqueues · timers · IRQ · DMA · BPF    │
├───────────────────────────────────────────────────────────────┤
│ ARCH: x86 / arm64 / riscv / loongarch / s390 / powerpc         │
└───────────────────────────────────────────────────────────────┘
```

**[DURABLE] Linux is a monolithic kernel with loadable modules.** Everything runs in one
address space at ring 0. There is no IPC boundary between the scheduler and your driver.
That is the source of both its performance and its blast radius: a NULL dereference in a
USB driver takes down the machine.

**The source tree, by orientation:**
| Directory | Contents |
|---|---|
| `kernel/` | Core: scheduler (`kernel/sched/`), signals, time, futex, cgroups, BPF (`kernel/bpf/`) |
| `mm/` | Memory management: page allocator, slab, VMA, page cache, swap, OOM |
| `fs/` | VFS + every filesystem (`ext4/`, `xfs/`, `btrfs/`, `overlayfs/`, `proc/`) |
| `drivers/` | **The majority of the tree.** By subsystem |
| `net/` | Protocol stacks, netfilter, sockets, XDP |
| `arch/` | Per-architecture: entry code, page tables, atomics, boot |
| `include/linux/` | Internal headers — the kernel's real API surface |
| `include/uapi/` | **The userspace ABI.** Change with extreme care (§4 → `linux-syscalls-ebpf-boot-and-init`) |
| `lib/`, `crypto/`, `security/`, `block/`, `ipc/`, `init/` | As named |
| `Documentation/` | **Read this.** It is unusually good and constantly out-of-date in exactly the places you'd expect |
| `tools/` | perf, bpftool, selftests, sched_ext examples |
| `rust/` | Rust core abstractions and the `kernel` crate (§2.6) |

### 1.2 Processes and threads

**[DURABLE] Linux has no separate "thread" concept in the kernel.** There is
`struct task_struct`, and threads are tasks that share resources. `clone()` with flags
decides *what* is shared:

| Flag | Shares |
|---|---|
| `CLONE_VM` | Address space → this is what makes it "a thread" |
| `CLONE_FS` | cwd, umask, root |
| `CLONE_FILES` | File descriptor table |
| `CLONE_SIGHAND` | Signal handlers |
| `CLONE_THREAD` | Thread group (same TGID → same "PID" to userspace) |
| `CLONE_NEWNS/NEWPID/NEWNET/…` | **Namespaces** — this is how containers are built (§7.3 → `linux-syscalls-ebpf-boot-and-init`) |

`fork()` = `clone()` with almost nothing shared. `pthread_create()` = `clone()` with
VM|FS|FILES|SIGHAND|THREAD. **Containers are the same primitive with namespace flags.**
There is no "container" object in the kernel — a container is a process with unusual
namespace, cgroup, and LSM settings.

**Process states** (`/proc/PID/stat`): R (running/runnable), S (interruptible sleep),
**D (uninterruptible sleep — waiting on I/O; cannot be killed, and a pile of D-state
processes means storage or a network filesystem is stuck)**, T (stopped), Z (zombie —
exited but not reaped; the parent's fault, not the child's), X (dead).

### 1.3 Scheduling

**Scheduling classes, in priority order** [VERSIONED — this list has grown]:
```
stop_sched_class     — CPU hotplug/migration. Preempts everything.
dl_sched_class       — SCHED_DEADLINE (EDF + constant bandwidth server)
rt_sched_class       — SCHED_FIFO, SCHED_RR (priorities 1–99)
fair_sched_class     — SCHED_NORMAL/BATCH/IDLE. EEVDF since 6.6 (replaced CFS)
ext_sched_class      — SCHED_EXT (sched_ext, BPF schedulers) — since 6.12
idle_sched_class     — the idle task
```

**EEVDF** (Earliest Eligible Virtual Deadline First) replaced CFS as the fair-class
algorithm in 6.6. The key concepts: each task accrues **virtual runtime** scaled by
weight (from `nice`); a task is **eligible** when its `vruntime` is at or behind the
weighted average; among eligible tasks the one with the earliest **virtual deadline**
runs. `sched_latency`-style tuning knobs from CFS largely don't apply; the per-task
`slice` (settable via `sched_setattr`) is the modern lever.

**[DURABLE] Real-time on Linux, precisely:**
- `SCHED_FIFO`/`SCHED_RR` tasks preempt all fair tasks and run until they block or yield.
  A runaway `SCHED_FIFO` task at priority 99 with a busy loop **hangs that CPU**;
  `sched_rt_runtime_us` (default 950000 of 1000000 µs) is the throttle that saves you.
- `SCHED_DEADLINE` takes (runtime, deadline, period) and does admission control — the
  kernel *refuses* to admit a task set it can't schedule. It's the only class with a
  real guarantee.
- **PREEMPT_RT was merged into mainline in Linux 6.12** (Sept 2024) for x86, arm64, and
  RISC-V, ending a ~20-year out-of-tree effort. This makes most spinlocks sleeping
  rt_mutexes and most IRQ handlers threaded. **It does not make Linux hard real-time** —
  it takes worst-case latency from milliseconds to tens of microseconds, which is a
  different claim.
- Achieving that in practice needs the whole stack: `isolcpus`/`nohz_full`/`rcu_nocbs`,
  IRQ affinity moved off isolated cores, `mlockall()`, no page faults in the hot path,
  C-states and frequency scaling pinned, and **`cyclictest` under representative load as
  proof**. A max-latency number without a load description is meaningless.

### 1.4 Memory

**Virtual memory layout** (x86-64, 4-level paging, 48-bit): userspace `0x0000...` up to
128 TiB, a non-canonical hole, then kernel space in the top half — direct map of all
physical memory, vmalloc area, kernel text. Since 5.x there is optional 5-level paging
(57-bit) for very large machines.

**Allocators, and when to use which** [DURABLE]:
| API | Backing | Size | Contiguity | Context |
|---|---|---|---|---|
| `kmalloc(size, gfp)` | slab | ≤ a few MB (order-limited) | **Physically contiguous** | Anywhere (gfp-dependent) |
| `kzalloc` / `kcalloc` | slab | " | " | Zeroed. Prefer these. |
| `vmalloc(size)` | pages + PTEs | large | Virtually only | **Sleeps.** Not for DMA |
| `alloc_pages(gfp, order)` | buddy | 2^order pages | Physically contiguous | Page granularity |
| `kmem_cache_alloc` | dedicated slab cache | fixed | contiguous | Hot objects of one type |
| `dma_alloc_coherent` | DMA API | | DMA-capable | **The only correct way to get DMA memory** |
| `devm_kzalloc` | slab, device-managed | | contiguous | **Auto-freed on driver detach — use it** |

**GFP flags are the most important thing to get right:**
- `GFP_KERNEL` — may sleep. **Cannot be used in atomic context** (interrupt handler,
  spinlock held, RCU read-side critical section).
- `GFP_ATOMIC` — will not sleep, may fail, dips into emergency reserves. Use in
  interrupt context.
- `GFP_NOWAIT` — no sleep, no reserves.
- `GFP_NOIO` / `GFP_NOFS` — may sleep but must not recurse into I/O or the filesystem.
  Required in block/fs writeback paths or you deadlock against yourself.
- `__GFP_ZERO`, `__GFP_NOWARN`, `__GFP_NOFAIL` (almost never justified).

> **⚠️ GOTCHA — sleeping in atomic context.** `might_sleep()` and
> `CONFIG_DEBUG_ATOMIC_SLEEP` exist because this is the single most common kernel bug
> class. `GFP_KERNEL` under a spinlock produces "BUG: sleeping function called from
> invalid context" — *if* you have the debug options on. If you don't, you get a rare,
> load-dependent deadlock in production instead. **Always develop with the debug configs
> enabled (§12.1 → `linux-kernel-debugging-process-and-hardening`).**

**The page cache** unifies file I/O and mmap: `read()` populates it, `mmap()` maps it,
writeback flushes dirty pages per `vm.dirty_ratio`/`dirty_background_ratio`. Understanding
this explains most Linux I/O behaviour, including why `free` "shows no free memory"
(cache is reclaimable and that's the point) and why `fsync()` is the only durability
primitive that means anything.

**The OOM killer** picks by `oom_score` (roughly, memory footprint adjusted by
`oom_score_adj`). Under cgroup v2, memory pressure is contained per-cgroup with
`memory.max` / `memory.high`, and **PSI** (`/proc/pressure/{cpu,memory,io}`) is the
modern signal for "this machine is thrashing" — far better than load average.

### 1.5 VFS and the block layer

```
syscall (read/write/openat)
  → VFS: struct file → struct dentry → struct inode → struct super_block
    → filesystem (ext4, xfs, btrfs, overlayfs, nfs, fuse…)
      → page cache
        → block layer: bio → request queue → I/O scheduler (mq-deadline, bfq, none)
          → blk-mq (multiqueue) → driver (nvme, virtio-blk, scsi)
```

**[DURABLE] The VFS's four objects** — superblock (a mounted fs), inode (a file's
metadata), dentry (a name→inode cache entry; the dcache is why path lookup is fast), and
file (an open file description, with the offset). Understanding that **dentries cache
names and inodes cache files** explains hard links, rename semantics, and why
`/proc/PID/fd` shows what it shows.

**Durability, correctly [DURABLE and constantly gotten wrong]:**
```
write()            → page cache. NOT durable. Survives process crash, not power loss.
fsync(fd)          → file data + metadata for that file to stable storage.
fdatasync(fd)      → data + only metadata needed to read it back. Cheaper.
fsync(dirfd)       → REQUIRED after create/rename/unlink to persist the DIRECTORY ENTRY.
O_SYNC / O_DSYNC   → implicit sync on each write. Slow.
O_DIRECT           → bypass page cache. Alignment requirements. Not a durability guarantee.
```
> **⚠️ GOTCHA — the atomic-rename recipe.** The only portable way to replace a file
> without risking a truncated result across a power loss:
> `open(tmp) → write() → fsync(tmp) → close → rename(tmp, target) → fsync(parent dir)`.
> Skipping the **parent directory fsync** is the step everyone omits, and it means the
> rename may not be durable even though the data is.
> Also: **`fsync()` can fail, and on Linux historically a failed `fsync()` could clear
> the error flag** — the "fsyncgate" problem that changed PostgreSQL's design. On error,
> the correct response is to treat the data as lost, not to retry.

**Filesystem selection** [VERSIONED]: **ext4** (default, boring, extremely well tested),
**XFS** (large files, high parallelism, online repair since ~6.18), **Btrfs** (CoW,
snapshots, checksums, subvolumes; RAID5/6 still not recommended), **ZFS** (out-of-tree,
CDDL/GPL licence incompatibility means it will never merge), **overlayfs** (the container
layering filesystem), **F2FS** (flash), **tmpfs**, **FUSE** (userspace).
**bcachefs** — see §17 → `linux-kernel-shell-reference`; it is no longer in the kernel tree.

### 1.6 Interrupts and deferred work

**[DURABLE] The two-half rule.** Hardware IRQ handlers run with interrupts disabled on
that line, cannot sleep, and must be as short as possible: acknowledge, grab the data,
schedule the rest.

| Mechanism | Context | Can sleep | Use for |
|---|---|---|---|
| Hard IRQ handler | interrupt | **No** | Ack hardware, wake the bottom half |
| **Threaded IRQ** (`request_threaded_irq`) | process | **Yes** | The modern default — the "bottom half" is a kernel thread |
| Softirq | interrupt (deferred) | No | Core subsystems only (net, block, timers). Don't add new ones |
| Tasklet | interrupt (deferred) | No | **Deprecated.** Use threaded IRQ or workqueue |
| **Workqueue** (`queue_work`) | process (kworker) | **Yes** | General deferred work. The right default |
| Kthread | process | Yes | Long-running per-device work |

**[VERSIONED] Write new drivers with `request_threaded_irq()`.** It gives you a sleeping
context for free and behaves correctly under PREEMPT_RT, where softirqs and tasklets have
different semantics.

---
