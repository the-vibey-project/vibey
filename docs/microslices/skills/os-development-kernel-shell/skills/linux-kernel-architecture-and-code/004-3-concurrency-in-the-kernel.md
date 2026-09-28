---
id: skill-3-concurrency-in-the-kernel-842823dc4c
purpose: 3 concurrency in the kernel
source: src/vibey_tools/skills/plugins/os-development-kernel-shell/skills/linux-kernel-architecture-and-code/SKILL.md
requires: ["skill-2-writing-kernel-code-edeffd33b4"]
links: []
---

## §3. Concurrency in the Kernel

### 3.1 The primitives

| Primitive | Sleeps | Context | Use for |
|---|---|---|---|
| `spinlock_t` | No (busy-waits) | Any, incl. IRQ | Short critical sections. **Under PREEMPT_RT these become sleeping rt_mutexes** |
| `spin_lock_irqsave/irqrestore` | No | When an IRQ handler takes the same lock | The safe default when in doubt |
| `raw_spinlock_t` | No, ever | Truly atomic paths | Stays a real spinlock even on RT |
| `struct mutex` | **Yes** | Process context only | Longer sections; the default choice |
| `rw_semaphore` | Yes | Process | Many readers, rare writers |
| `seqlock_t` | No | Any | Read-mostly; readers retry, never block writers |
| **RCU** | Readers: no | Any | **Read-mostly data structures. The kernel's signature technique** |
| `atomic_t` / `atomic64_t` | No | Any | Counters, flags |
| `refcount_t` | No | Any | **Reference counts — use this, not atomic_t.** It detects overflow/UAF |
| `completion` | Yes | Process | "Wait until this finishes" |
| `wait_queue_head_t` | Yes | Process | Sleep until a condition |
| `percpu` variables | — | Any | Avoid sharing entirely — the fastest lock is no lock |

### 3.2 RCU — the thing that makes Linux scale

**[DURABLE] Read-Copy-Update:** readers are (almost) free — no locks, no atomics, no
cache-line bouncing. Writers make a *copy*, publish it atomically, and defer freeing the
old version until every pre-existing reader has finished.

```c
/* Reader — cheap. rcu_read_lock() is essentially a preempt-disable. */
rcu_read_lock();
p = rcu_dereference(gp);            /* ensures the load isn't reordered ahead */
if (p) do_something(p->field);      /* p is guaranteed valid until unlock */
rcu_read_unlock();

/* Writer */
new = kmalloc(sizeof(*new), GFP_KERNEL);
*new = *old;
new->field = value;
rcu_assign_pointer(gp, new);        /* publish: barrier + store */
synchronize_rcu();                  /* wait for a GRACE PERIOD (may sleep, may be slow) */
kfree(old);
/* or: call_rcu(&old->rcu, free_cb);  — async, doesn't block the writer */
```
**The grace period** is the whole idea: a period after which every CPU has passed through
a quiescent state, so no reader can still hold the old pointer.

> **⚠️ GOTCHA — RCU read-side is atomic context.** You cannot sleep between
> `rcu_read_lock()` and `rcu_read_unlock()`. No `GFP_KERNEL`, no mutex, no
> `copy_to_user`. (SRCU exists if you need to sleep; it has its own costs.)
> `CONFIG_PROVE_RCU` catches violations.

### 3.3 Memory barriers

**[DURABLE] The compiler and the CPU both reorder memory accesses.** The kernel's model
is documented in `Documentation/memory-barriers.txt` — long, dense, and the definitive
source.

| Barrier | Effect |
|---|---|
| `barrier()` | Compiler only |
| `smp_mb()` | Full barrier (SMP only; compiles away on UP) |
| `smp_rmb()` / `smp_wmb()` | Read / write barrier |
| `smp_store_release()` / `smp_load_acquire()` | **The preferred modern idiom.** Cheaper than full barriers and expresses intent |
| `mb()`, `rmb()`, `wmb()` | Including for MMIO/DMA |
| `READ_ONCE()` / `WRITE_ONCE()` | Prevent the compiler from tearing, fusing, or inventing accesses |

**[DURABLE] `volatile` is nearly always wrong in kernel code.** Use `READ_ONCE`/
`WRITE_ONCE` for single accesses and proper locking or barriers for ordering.
`Documentation/process/volatile-considered-harmful.rst` exists for a reason.

### 3.4 The deadlock rules

1. **Establish a global lock ordering and document it.** Nested locks must always be
   taken in the same order everywhere.
2. **Never sleep holding a spinlock.**
3. **If an IRQ handler takes lock L, every other acquirer of L must disable interrupts**
   (`spin_lock_irqsave`), or you deadlock against yourself.
4. **Prefer one lock over two.** Prefer per-CPU or RCU over one.
5. **Turn on lockdep** (`CONFIG_PROVE_LOCKING`). It builds a lock dependency graph at
   runtime and reports a potential deadlock the first time it sees an inconsistent
   ordering — *even if the deadlock doesn't happen*. It is one of the best debugging
   tools in any system, anywhere.
