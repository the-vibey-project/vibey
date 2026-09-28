---
id: skill-5-design-patterns-the-working-set-8fbe7463ae
purpose: 5 design patterns the working set
source: src/vibey_tools/skills/plugins/embedded-iot-controls/skills/embedded-languages-realtime-and-patterns/SKILL.md
requires: ["skill-4-concurrency-timing-and-real-time-correctness-0b441e02f0"]
links: []
---

## §5. Design Patterns — the working set

### 5.1 Layered architecture, and why it matters for testing

```
┌─────────────────────────────────────────────┐
│ Application  — business logic, state machines│  ← 100% host-testable
├─────────────────────────────────────────────┤
│ Services     — logging, config, comms, OTA   │  ← host-testable w/ fakes
├─────────────────────────────────────────────┤
│ Device drivers — sensor.c, motor.c, radio.c  │  ← testable against a fake bus
├─────────────────────────────────────────────┤
│ HAL / BSP    — i2c_write(), gpio_set()       │  ← the seam. ONE header per bus.
├─────────────────────────────────────────────┤
│ Vendor SDK / registers                       │  ← target only
└─────────────────────────────────────────────┘
```
**[UNIVERSAL] The single highest-leverage architectural decision in firmware is putting a
narrow, dependency-injected seam between drivers and hardware.** Everything above the seam
becomes unit-testable on a host machine, in a CI pipeline, in milliseconds. Teams that do
this find bugs 100× faster than teams that only test on hardware.

```c
/* The seam: an interface struct, not a global function. Enables fakes. */
typedef struct i2c_bus {
    int (*write)(void *ctx, uint8_t addr, const uint8_t *d, size_t n);
    int (*read )(void *ctx, uint8_t addr,       uint8_t *d, size_t n);
    void *ctx;
} i2c_bus_t;

/* Driver depends on the interface, never on the vendor HAL. */
typedef struct { const i2c_bus_t *bus; uint8_t addr; } bme280_t;

int bme280_read_temp(bme280_t *dev, int32_t *out_millideg) {
    uint8_t reg = 0xFA, raw[3];
    int rc = dev->bus->write(dev->bus->ctx, dev->addr, &reg, 1);
    if (rc != 0) return rc;
    rc = dev->bus->read(dev->bus->ctx, dev->addr, raw, sizeof raw);
    if (rc != 0) return rc;
    *out_millideg = bme280_compensate(raw);   /* pure function — trivially testable */
    return 0;
}
```
No heap, no globals, no vtable cost beyond one indirect call, and `bme280_compensate` can
be tested against the datasheet's reference values without any hardware at all.

### 5.2 State machines — pick the right form

| Form | Best when | Cost |
|---|---|---|
| `switch` on enum | ≤5 states, few events | Simplest; degrades badly with growth |
| **State table** (2-D array of handlers) | Many states × events, uniform | Data-driven, compact, easy to audit/verify |
| Function-pointer state | States have distinct entry/exit behaviour | Idiomatic C; O(1) dispatch |
| **Hierarchical (HSM/statechart)** | Shared behaviour across states, "cancel from any state" | Miro Samek's QP; eliminates duplicated transitions |
| Generated (Zephyr SMF, Yakindu, Stateflow) | Formal spec exists / cert required | Traceability; tool lock-in |

```c
/* State table — the workhorse. Adding a state or event is a table edit, not surgery. */
typedef enum { ST_IDLE, ST_ARMING, ST_RUNNING, ST_FAULT, ST_COUNT } state_t;
typedef enum { EV_START, EV_STOP, EV_TICK, EV_FAULT, EV_COUNT } event_t;

typedef state_t (*handler_t)(void *ctx);
static state_t on_idle_start(void *c);   /* ... */

static const handler_t fsm[ST_COUNT][EV_COUNT] = {
    /*             EV_START        EV_STOP        EV_TICK        EV_FAULT   */
    [ST_IDLE]    = { on_idle_start,  NULL,          NULL,          on_fault   },
    [ST_ARMING]  = { NULL,           on_abort,      on_arm_tick,   on_fault   },
    [ST_RUNNING] = { NULL,           on_stop,       on_run_tick,   on_fault   },
    [ST_FAULT]   = { NULL,           on_fault_ack,  NULL,          NULL       },
};

void fsm_dispatch(fsm_ctx_t *ctx, event_t ev) {
    handler_t h = fsm[ctx->state][ev];
    if (h == NULL) { log_unhandled(ctx->state, ev); return; }  /* explicit, not silent */
    state_t next = h(ctx);
    if (next != ctx->state) {
        state_exit(ctx, ctx->state);      /* run-to-completion: exit, then entry */
        ctx->state = next;
        state_entry(ctx, next);
    }
}
```
**[UNIVERSAL] Run-to-completion semantics**: an event is processed fully before the next
is dequeued. This is what makes statecharts analyzable. Never process an event from inside
a state handler — post it to the queue instead.

**Active Object pattern** (Samek's QP, and the model behind Zephyr's message queues): each
component is a state machine + an event queue + a thread; components communicate only by
posting events. No shared mutable state → no mutexes → no priority inversion → no
deadlocks. This is the strongest general architecture for medium-to-large firmware and is
worth reading *Practical UML Statecharts in C/C++* for.

### 5.3 Lock-free SPSC ring buffer — the one you'll write a hundred times

```c
/* Single-producer (ISR) / single-consumer (task). No locks. Capacity must be a
   power of two. Uses the full range of the index type and lets it WRAP —
   this is why unsigned overflow being well-defined matters. */
typedef struct {
    uint8_t  buf[RB_SIZE];             /* RB_SIZE must be a power of 2 */
    volatile uint32_t head;            /* written ONLY by producer */
    volatile uint32_t tail;            /* written ONLY by consumer */
} ringbuf_t;

_Static_assert((RB_SIZE & (RB_SIZE - 1)) == 0, "RB_SIZE must be a power of two");

static inline uint32_t rb_count(const ringbuf_t *r) { return r->head - r->tail; }
static inline bool     rb_full (const ringbuf_t *r) { return rb_count(r) == RB_SIZE; }
static inline bool     rb_empty(const ringbuf_t *r) { return r->head == r->tail; }

/* Producer side — call from ISR only */
bool rb_push(ringbuf_t *r, uint8_t v) {
    if (rb_full(r)) return false;                    /* drop, or overwrite: choose deliberately */
    r->buf[r->head & (RB_SIZE - 1)] = v;
    __DMB();                                         /* data visible BEFORE index advance */
    r->head++;                                       /* single word, atomic on 32-bit */
    return true;
}

/* Consumer side — call from task only */
bool rb_pop(ringbuf_t *r, uint8_t *out) {
    if (rb_empty(r)) return false;
    *out = r->buf[r->tail & (RB_SIZE - 1)];
    __DMB();                                         /* read data BEFORE releasing slot */
    r->tail++;
    return true;
}
```
**Why it's correct**: exactly one writer per index; the power-of-two mask makes wraparound
free; the difference `head - tail` is correct across rollover because unsigned arithmetic
wraps. **Why it breaks**: two producers, or two consumers, or a non-power-of-two size, or
omitting the barriers on a machine with a write buffer.

**⚠️ GOTCHA — the "one slot wasted" alternative.** Many textbook ring buffers compare
`(head+1)%N == tail` to detect full, wasting a slot. The counting version above uses the
whole buffer but requires that the index type is wide enough that `head - tail` can never
legitimately exceed the buffer size — which it can't, since we never push when full.

### 5.4 Memory pools instead of malloc

```c
/* Fixed-block allocator: O(1), no fragmentation, deterministic. */
typedef struct block { struct block *next; } block_t;

typedef struct {
    block_t *free_list;
    uint8_t *storage;
    size_t   block_size, count;
} pool_t;

void pool_init(pool_t *p, void *mem, size_t block_size, size_t count) {
    p->storage = mem; p->block_size = block_size; p->count = count;
    p->free_list = NULL;
    for (size_t i = 0; i < count; i++) {                  /* thread the free list */
        block_t *b = (block_t *)(p->storage + i * block_size);
        b->next = p->free_list;
        p->free_list = b;
    }
}
void *pool_alloc(pool_t *p) {
    uint32_t s = critical_enter();
    block_t *b = p->free_list;
    if (b) p->free_list = b->next;
    critical_exit(s);
    return b;                                             /* NULL if exhausted — CHECK IT */
}
void pool_free(pool_t *p, void *blk) {
    uint32_t s = critical_enter();
    ((block_t *)blk)->next = p->free_list;
    p->free_list = blk;
    critical_exit(s);
}
```
Pattern: one pool per message size class, sized at design time from the worst-case
in-flight count. Exhaustion is then a *design* question you answer before shipping, not a
runtime surprise.

### 5.5 Time handling — rollover-safe, always

```c
/* WRONG: breaks every 49.7 days on a 32-bit ms counter, and immediately if the
   deadline computation wraps. This bug ships constantly. */
if (millis() > deadline) { ... }

/* RIGHT: signed difference. Works across rollover for intervals < 2^31 ms (~24 days). */
static inline bool time_after(uint32_t a, uint32_t b) {
    return (int32_t)(a - b) > 0;
}
if (time_after(millis(), deadline)) { ... }

/* Elapsed time — always subtract, never compare absolutes */
uint32_t start = millis();
/* ... */
uint32_t elapsed = millis() - start;   /* correct across wrap */
```
**[UNIVERSAL] Rules of embedded time:**
1. Use a **monotonic** counter for intervals; never wall-clock (it jumps on NTP/RTC sync).
2. Always compute **differences**, never compare absolute timestamps.
3. Know your counter width and pick an interval type that can't exceed half of it.
4. `k_uptime_get()` (Zephyr, 64-bit) and `esp_timer_get_time()` (64-bit µs) sidestep the
   problem — use 64-bit where available.

**Debouncing** — two correct approaches:
```c
/* 1. Integrator (noise-immune, no fixed delay): sample at fixed rate */
static uint8_t integrator = 0;
#define DEBOUNCE_MAX 10
bool debounce_sample(bool raw) {
    if (raw && integrator < DEBOUNCE_MAX) integrator++;
    else if (!raw && integrator > 0)      integrator--;
    if (integrator == 0)            return false;   /* stable low  */
    if (integrator == DEBOUNCE_MAX) return true;    /* stable high */
    return last_stable;                             /* hysteresis zone */
}

/* 2. Shift register (fast, 1 line): N consecutive identical samples */
static uint16_t hist = 0;
bool debounce_shift(bool raw) {
    hist = (uint16_t)((hist << 1) | (raw ? 1u : 0u));
    if ((hist & 0x00FF) == 0x00FF) return true;
    if ((hist & 0x00FF) == 0x0000) return false;
    return last_stable;
}
```
Never `delay(50)` in a button handler. Never poll a button in a busy loop.

### 5.6 Driver patterns

**Blocking → non-blocking → interrupt → DMA** is a progression, and the API shape should
reflect where you are:
```c
/* Blocking: fine for init-time, fatal in a control loop */
int spi_transfer(const uint8_t *tx, uint8_t *rx, size_t n);

/* Non-blocking with completion callback: the general-purpose shape */
typedef void (*xfer_done_t)(void *ctx, int status);
int spi_transfer_async(const uint8_t *tx, uint8_t *rx, size_t n,
                       xfer_done_t cb, void *ctx);

/* Callback runs in ISR context → it must only signal, never process.
   This is the ISR→task handoff (5.7). */
```

**Bus arbitration**: when multiple tasks share an SPI/I²C bus, own the bus with a **mutex**
held for the duration of a *transaction* (CS assert → transfer → CS deassert), not per
byte. Wrap it in RAII (C++) or a `bus_lock()/bus_unlock()` pair with a timeout, and treat
timeout as a hard error worth logging, not a retry-forever.

**Double-buffered / ping-pong DMA** — the pattern for continuous acquisition:
```
DMA circular mode with half-transfer + transfer-complete interrupts:
  HT  interrupt → process first half   while DMA fills second half
  TC  interrupt → process second half  while DMA fills first half
No gaps, no missed samples, CPU touched only twice per buffer.
```
**⚠️ GOTCHA (M7)**: invalidate the D-cache for the half you're about to read (§1.2 → `embedded-silicon-and-firmware-models`).

### 5.7 ISR-to-task handoff — the canonical FreeRTOS form

```c
/* Highest-value 20 lines in an RTOS codebase. Get this shape right everywhere. */
static TaskHandle_t s_worker;                  /* set at task creation */

void UART_IRQHandler(void) {
    BaseType_t higher_woken = pdFALSE;

    if (UART->ISR & UART_ISR_RXNE) {
        uint8_t b = (uint8_t)UART->RDR;        /* read clears the flag on most parts */
        (void)rb_push(&rx_ring, b);            /* lock-free; ISR is sole producer */

        /* Notify, don't process. Notification is faster than a semaphore. */
        vTaskNotifyGiveFromISR(s_worker, &higher_woken);
    }
    if (UART->ISR & UART_ISR_ORE) {            /* overrun: count it, don't ignore it */
        UART->ICR = UART_ICR_ORECF;
        s_diag.uart_overruns++;
    }

    /* If we woke a task of higher priority than the interrupted one,
       request a context switch on ISR exit — otherwise latency is one tick. */
    portYIELD_FROM_ISR(higher_woken);
}

void worker_task(void *arg) {
    for (;;) {
        /* Block until notified; the count tells us how many notifications we missed. */
        (void)ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
        uint8_t b;
        while (rb_pop(&rx_ring, &b)) {
            protocol_feed(b);                  /* all real work happens here */
        }
    }
}
```
**Three things people get wrong**: forgetting `portYIELD_FROM_ISR` (adds up to one tick of
latency), calling a non-`FromISR` API from an ISR (corrupts the kernel), and running the
ISR at a priority above `configMAX_SYSCALL_INTERRUPT_PRIORITY` while calling kernel APIs
(silent, intermittent corruption — see §1.1 → `embedded-silicon-and-firmware-models` gotcha).

### 5.8 Error handling and fault forensics

**[UNIVERSAL] The three-tier model:**
1. **Expected, recoverable** → return an error code. Every caller checks it.
   `[[nodiscard]]`/`__attribute__((warn_unused_result))` makes ignoring it a warning.
2. **Programmer error / impossible state** → `assert`. In development, halt and inspect.
   In production, **do not silently compile it out** — record it and reset (a controlled
   reset with a logged reason beats undefined behaviour).
3. **Hardware fault** → fault handler that captures state and resets.

```c
/* Production assert: record, then reset. Never NDEBUG your asserts away silently. */
void assert_failed(const char *file, uint32_t line) {
    __disable_irq();
    s_crash.magic = CRASH_MAGIC;                 /* in .noinit — survives soft reset */
    s_crash.kind  = CRASH_ASSERT;
    s_crash.line  = line;
    strncpy(s_crash.file, file, sizeof s_crash.file - 1);
    /* flush to backup RAM / RTC domain if available */
    NVIC_SystemReset();
}
```

**HardFault handler that actually tells you something** — this is worth its weight in gold:
```c
/* Naked wrapper: figure out which stack was in use, pass the frame to C. */
__attribute__((naked)) void HardFault_Handler(void) {
    __asm volatile (
        "tst   lr, #4          \n"   /* EXC_RETURN bit 2: 0=MSP, 1=PSP */
        "ite   eq              \n"
        "mrseq r0, msp         \n"
        "mrsne r0, psp         \n"
        "mov   r1, lr          \n"
        "b     hardfault_c     \n"
    );
}

typedef struct {           /* the hardware-stacked exception frame */
    uint32_t r0, r1, r2, r3, r12, lr, pc, psr;
} exc_frame_t;

void hardfault_c(exc_frame_t *frame, uint32_t exc_return) {
    s_crash.magic = CRASH_MAGIC;
    s_crash.kind  = CRASH_HARDFAULT;
    s_crash.pc    = frame->pc;       /* ← the faulting instruction. Look it up in the .map */
    s_crash.lr    = frame->lr;       /* ← the caller */
    s_crash.psr   = frame->psr;
    s_crash.cfsr  = SCB->CFSR;       /* Configurable Fault Status: which fault, precisely */
    s_crash.hfsr  = SCB->HFSR;       /* HardFault Status (FORCED bit ⇒ escalated) */
    s_crash.mmfar = SCB->MMFAR;      /* MemManage Fault Address — valid if CFSR.MMARVALID */
    s_crash.bfar  = SCB->BFAR;       /* BusFault Address     — valid if CFSR.BFARVALID   */
    s_crash.exc_return = exc_return;
    /* Optionally: walk the stack for plausible return addresses to build a backtrace. */
    NVIC_SystemReset();
}
```
**Decoding CFSR** (the bits you'll actually see):
- `IACCVIOL` — instruction fetch from a non-executable region → jumped through a bad
  function pointer.
- `PRECISERR` + valid `BFAR` — dereferenced a bad address; BFAR tells you which.
- `IMPRECISERR` — a buffered write faulted later; disable write buffering
  (`SCB->ACTLR |= DISDEFWBUF`) during debug to make it precise.
- `UNALIGNED` — unaligned access with `UNALIGN_TRP` enabled, or an unaligned `LDM/STM`.
- `UNDEFINSTR` — executed garbage, or called an FPU instruction with the FPU disabled.
  **The FPU one is extremely common**: enabling `-mfpu=fpv4-sp-d16` without enabling
  CP10/CP11 in `CPACR` faults on the first float operation.
- `STKERR`/`UNSTKERR` — stack overflow during exception entry/exit.

**Enable the specific fault handlers.** By default, MemManage/BusFault/UsageFault escalate
to HardFault, losing information. Set `SCB->SHCSR |= MEMFAULTENA | BUSFAULTENA |
USGFAULTENA` at boot so you get the precise handler and a meaningful `HFSR.FORCED == 0`.

### 5.9 The supervised watchdog

```c
/* Each critical task registers and periodically checks in. A single supervisor
   verifies ALL tasks are alive within their deadlines before kicking the IWDG. */
typedef struct { uint32_t last_ms; uint32_t deadline_ms; const char *name; } wdt_client_t;
static wdt_client_t clients[WDT_MAX_CLIENTS];
static uint32_t     registered_mask;
static volatile uint32_t checkin_mask;

void wdt_checkin(uint8_t id) {
    clients[id].last_ms = millis();
    __atomic_or_fetch(&checkin_mask, 1u << id, __ATOMIC_RELAXED);
}

void wdt_supervisor_tick(void) {              /* run at, say, 10 Hz */
    uint32_t now = millis();
    for (uint8_t i = 0; i < WDT_MAX_CLIENTS; i++) {
        if (!(registered_mask & (1u << i))) continue;
        if ((uint32_t)(now - clients[i].last_ms) > clients[i].deadline_ms) {
            s_crash.kind = CRASH_WDT_STARVED;
            strncpy(s_crash.file, clients[i].name, sizeof s_crash.file - 1);
            return;                            /* DO NOT kick — let the IWDG fire */
        }
    }
    IWDG->KR = 0xAAAA;                         /* all healthy: kick */
}
```
This turns "the system hung" into "task `comms` missed its 500 ms deadline" in your fleet
telemetry.

### 5.10 The anti-pattern catalogue

| Anti-pattern | Why it's bad | Do instead |
|---|---|---|
| `delay()`/`HAL_Delay()` in production logic | Burns CPU, blocks everything, destroys real-time | Non-blocking timers, RTOS `vTaskDelay`, state machines |
| Work inside an ISR | Latency, priority inversion, unbounded jitter | Signal + defer to task |
| `malloc`/`free` at runtime | Fragmentation, non-determinism, silent OOM | Static allocation or fixed pools |
| Global variables everywhere | Untestable, racy, unfollowable data flow | Context structs passed explicitly |
| Ignoring return codes | Failures propagate silently, corrupt state | `[[nodiscard]]`, check every one |
| Magic numbers | Unmaintainable; unit errors | Named constants w/ units in the name (`TIMEOUT_MS`) |
| Copy-pasted drivers | Bug fixed in one copy, not the other four | One driver, parameterized |
| `while(!(REG & FLAG));` with no timeout | Infinite hang on hardware fault | Bounded wait + error return |
| Busy-wait polling | Burns power, blocks | Interrupt or `__WFI()` |
| Kicking watchdog from a timer ISR | Proves nothing; masks hangs | Supervised watchdog (§5.9) |
| One giant `main.c` | Untestable, unreviewable | Layered modules (§5.1) |
| Floating-point in an ISR without FPU context save | Corrupts task FP state | Enable lazy stacking, or keep FP out of ISRs |
| Unbounded recursion | Stack overflow, unanalyzable | Iteration; MISRA bans recursion outright |
| Testing only on hardware | Slow loop, poor coverage, no CI | Host tests + fakes (§12 → `embedded-security-safety-and-testing`) |
