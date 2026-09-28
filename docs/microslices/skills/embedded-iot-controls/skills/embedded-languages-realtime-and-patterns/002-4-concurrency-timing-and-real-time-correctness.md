---
id: skill-4-concurrency-timing-and-real-time-correctness-0b441e02f0
purpose: 4 concurrency timing and real time correctness
source: src/vibey_tools/skills/plugins/embedded-iot-controls/skills/embedded-languages-realtime-and-patterns/SKILL.md
requires: ["skill-3-languages-737593fbec"]
links: ["skill-5-design-patterns-the-working-set-8fbe7463ae"]
---

## §4. Concurrency, Timing, and Real-Time Correctness

### 4.1 Real-time taxonomy [UNIVERSAL]

- **Hard real-time**: a missed deadline is a **system failure**. Airbag deployment, motor
  commutation, safety interlocks. Requires provable WCET and a scheduler you can analyze.
- **Firm real-time**: a late result is **useless** but not catastrophic. Video frame,
  sensor sample in a fusion window.
- **Soft real-time**: a late result **degrades quality**. UI responsiveness, telemetry
  upload.

**"Real-time" does not mean "fast."** A system that responds in 10 ms *always* is
real-time; one that responds in 100 µs *usually* and 50 ms *occasionally* is not.
Determinism is the property; speed is incidental.

**WCET (worst-case execution time)** is genuinely hard on modern parts: caches, branch
prediction, DMA bus contention, and flash wait states all make measured-average wildly
optimistic. Approaches, in order of rigour:
1. **Static WCET analysis** (aiT, Bound-T) — sound but expensive and needs a processor
   model.
2. **Measurement-based with instrumentation** — GPIO toggle at entry/exit, capture with a
   scope or logic analyzer; run pathological inputs deliberately.
3. **Cycle counters** — `DWT->CYCCNT` on Cortex-M3+ gives you free cycle-accurate timing.
4. **Add margin.** Typical practice: design to ≤50–70% CPU utilization so that measurement
   error and future features don't eat your margin.

```c
/* DWT cycle counter — the cheapest accurate profiler on Cortex-M3+ */
static inline void cyccnt_enable(void) {
    CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;
    DWT->CYCCNT = 0;
    DWT->CTRL  |= DWT_CTRL_CYCCNTENA_Msk;
}
#define CYCCNT_START()  uint32_t _t0 = DWT->CYCCNT
#define CYCCNT_ELAPSED() (DWT->CYCCNT - _t0)   /* unsigned: wrap-safe */
```

### 4.2 Critical sections — the cost you keep paying

```c
/* Coarse: disables ALL interrupts including the 10 kHz control loop. */
__disable_irq();
shared_state.a = x;
shared_state.b = y;
__enable_irq();

/* Better on Cortex-M: BASEPRI masks only interrupts at/below a priority.
   Your highest-priority "kernel-transparent" ISRs keep running. */
static inline uint32_t critical_enter(void) {
    uint32_t prev = __get_BASEPRI();
    __set_BASEPRI(CRITICAL_PRIORITY << (8 - __NVIC_PRIO_BITS));
    __DMB();
    return prev;
}
static inline void critical_exit(uint32_t prev) {
    __DMB();
    __set_BASEPRI(prev);
}
```
**⚠️ GOTCHA — nesting.** `__enable_irq()` unconditionally enables. If a critical section
nests inside another, the inner exit re-enables interrupts early. **Always save and
restore** the previous mask (as above), never blind enable/disable.

**[UNIVERSAL] The best critical section is the one you don't take.** Prefer:
lock-free SPSC structures (§5.3), atomic single-word updates, double-buffering, and
message passing over shared mutable state.

### 4.3 Atomics and memory barriers

- On a single-core Cortex-M, **aligned 32-bit loads and stores are atomic**. A `uint32_t`
  written by an ISR and read by a task needs no lock — but does need `volatile` (or
  `atomic_load_explicit`) so the compiler doesn't cache it.
- **Read-modify-write is NOT atomic.** `counter++` is load/add/store; an ISR between the
  load and store loses the increment. Use `LDREX/STREX` (via `atomic_fetch_add` or
  `__atomic_*` builtins), or a critical section.
- **`volatile` provides no ordering guarantees between different variables** and no
  hardware barrier. On Cortex-M's mostly-in-order, non-speculative memory model you often
  get away with it; on Cortex-A, multicore, or with a write buffer in front of a
  peripheral, you do not.
- Barriers: `__DMB()` (data memory barrier — orders memory accesses), `__DSB()` (data
  synchronization barrier — waits for completion), `__ISB()` (instruction sync — flushes
  the pipeline; required after changing the vector table, MPU config, or when
  self-modifying).
- **The canonical pattern**: after writing a register that changes execution behaviour
  (MPU enable, VTOR, NVIC disable before a critical operation), issue `__DSB(); __ISB();`.

```c
/* Correct ISR→task flag with C11 atomics */
#include <stdatomic.h>
static atomic_bool  data_ready = false;
static uint8_t      buffer[N];             /* only ISR writes before flag set */

void DMA_IRQHandler(void) {
    /* ... DMA filled buffer ... */
    atomic_store_explicit(&data_ready, true, memory_order_release);  /* publishes buffer */
}

void task(void) {
    if (atomic_load_explicit(&data_ready, memory_order_acquire)) {   /* acquires buffer */
        process(buffer);
        atomic_store_explicit(&data_ready, false, memory_order_relaxed);
    }
}
```
Release/acquire is what makes the buffer contents visible — a plain `volatile bool` does
not guarantee that on an out-of-order or write-buffered machine.

### 4.4 The concurrency bug taxonomy

| Bug | Signature | Fix |
|---|---|---|
| **Race condition** | Works on debug build, fails at -O2 or under load | Atomics, locks, single-writer discipline |
| **Priority inversion** | High-priority task misses deadline sporadically | Priority inheritance mutexes |
| **Deadlock** | System hangs, watchdog fires | Lock ordering discipline; never take two locks; timeouts on every take |
| **Livelock** | 100% CPU, no progress | Backoff; check retry loops |
| **Lost wakeup** | Task sleeps forever despite event | Check-then-wait must be atomic; use notification counters not flags |
| **Torn read** | Multi-word value (64-bit timestamp, struct) partially updated | Double-buffer, seqlock, or critical section |
| **ABA** | Lock-free structure corrupts | Tagged pointers / generation counters |
| **Stack overflow** | Corruption of an unrelated variable | MPU guard + high-water marks |

> **⚠️ GOTCHA — the 64-bit timestamp tear.** A 32-bit MCU cannot atomically read a 64-bit
> microsecond counter maintained by an ISR. Reading `hi` then `lo` can straddle a
> rollover. Use the **seqlock** pattern: reader reads a sequence counter, reads the data,
> re-reads the counter, retries if it changed or is odd.

---
