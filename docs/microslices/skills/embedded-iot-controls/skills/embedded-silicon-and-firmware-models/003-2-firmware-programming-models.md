---
id: skill-2-firmware-programming-models-8ca77c9d31
purpose: 2 firmware programming models
source: src/vibey_tools/skills/plugins/embedded-iot-controls/skills/embedded-silicon-and-firmware-models/SKILL.md
requires: ["skill-1-silicon-memory-and-peripherals-73dbb370c6"]
links: []
---

## §2. Firmware Programming Models

### 2.1 Register-level vs HAL — the real trade

**[CONTESTED]** This is one of the field's oldest arguments. Steelman both:

**Case for vendor HALs (STM32 HAL, ESP-IDF, nRF Connect SDK, TI DriverLib):**
- Errata workarounds are already implemented. Silicon errata sheets are 60 pages and you
  will not read them all.
- Peripheral initialization sequences on modern parts are genuinely intricate (USB, DDR,
  Ethernet, LTDC). Hand-rolling them is weeks of work with no product differentiation.
- They encode the "insert dummy read after clock enable" class of undocumented-ish
  requirements.
- Portability across a vendor's family is real and valuable for product lines.
- Time-to-first-working-prototype is 10× better.

**Case for registers (or thin LL layers):**
- HALs are large: STM32 HAL adds tens of KB and blocking APIs with `HAL_MAX_DELAY`
  spin-waits that are unusable in real-time paths.
- HAL state machines duplicate and fight the RTOS's state machine.
- You cannot reason about worst-case timing through code you haven't read.
- HAL bugs exist and you'll debug them anyway — at which point you've paid the HAL cost
  *and* the register cost.
- Some HALs (older STM32 HAL) have genuinely poor error handling and race conditions in
  DMA paths.

**The synthesis most experienced teams land on:** use the HAL/SDK for *initialization*
(clocks, pin mux, complex peripherals) and for anything you'd never differentiate on;
write **thin, direct register drivers for the hot path** (the ADC-to-control-loop path,
the high-rate SPI transfer). Wrap both behind *your own* interface so the application
never sees vendor types. That last point is what makes the code testable (§12.2 → `embedded-security-safety-and-testing`).

**CMSIS** is the layer worth knowing regardless: `CMSIS-Core` gives you the standard
`NVIC_*`, `__DSB/__DMB/__ISB`, `SCB->*` definitions and the device header with every
peripheral struct. `CMSIS-DSP` gives you well-optimized FFT/filter/matrix routines with
Q7/Q15/Q31/f32 variants. `CMSIS-NN` gives you quantized NN kernels for Cortex-M.

### 2.2 The superloop and its disciplined variants

```c
/* Naive superloop — fine for genuinely simple systems, a trap for anything else */
int main(void) {
    hw_init();
    for (;;) {
        read_sensors();
        run_control();
        update_outputs();
        service_comms();
    }
}
```
Problems appear the moment any of these can block or has a different natural rate.

**Time-triggered / cooperative scheduler** — the underrated middle ground:
```c
typedef struct {
    void   (*task)(void);
    uint32_t period_ms;
    uint32_t next_due;   /* monotonic ms */
} sched_slot_t;

static sched_slot_t slots[] = {
    { task_control,  1,   0 },   /* 1 kHz */
    { task_sensors, 10,   0 },
    { task_comms,   50,   0 },
    { task_health, 1000,  0 },
};

void scheduler_run(void) {
    for (;;) {
        uint32_t now = millis();                 /* monotonic, wraps */
        for (size_t i = 0; i < ARRAY_LEN(slots); i++) {
            /* rollover-safe comparison — see §5.5 */
            if ((int32_t)(now - slots[i].next_due) >= 0) {
                slots[i].next_due = now + slots[i].period_ms;
                slots[i].task();
            }
        }
        __WFI();  /* sleep until next interrupt */
    }
}
```
This gives you: deterministic execution order, no stack-per-task cost, no priority
inversion, trivially analyzable timing — at the cost of requiring every task to be
non-blocking and short. Jack Ganssle and the time-triggered-architecture literature
(Pont) argue this is the right default for safety-relevant small systems.

### 2.3 RTOS landscape (2026)

| RTOS | Governance | Licence | Footprint (kernel) | Killer feature | Weakness |
|---|---|---|---|---|---|
| **FreeRTOS** | AWS | MIT | ~6–12 KB | Ubiquity, simplicity, LTS + Extended Maintenance Plan, SMP since v11 | Kernel only — you assemble drivers/stack yourself |
| **Zephyr** | Linux Foundation | Apache-2.0 | ~8 KB min, realistically 30–100 KB with subsystems | Devicetree + Kconfig, huge in-tree driver/BSP set, full networking, MCUboot, PM subsystem | Steep learning curve; build system opinionated; churn between releases |
| **ThreadX (Eclipse ThreadX)** | Eclipse Foundation | MIT | ~2–20 KB | Pre-certified safety artifacts, very small, deterministic | Post-Microsoft-donation ecosystem still settling |
| **NuttX** | Apache | Apache-2.0 | varies | POSIX-conformant — port Linux code nearly unchanged | Heavier; smaller community than Zephyr |
| **RT-Thread** | RT-Thread | Apache-2.0 | ~3 KB | Dominant in China; huge component ecosystem | Docs/English support uneven |
| **QNX** | BlackBerry | Commercial | MB-class | Microkernel, true hard RT, safety-certified, automotive standard | Cost; MPU-class only |
| **VxWorks** | Wind River | Commercial | MB-class | Aerospace/defence pedigree, DO-178C artifacts | Cost |
| **SafeRTOS** | WITTENSTEIN | Commercial | small | IEC 61508 SIL 3 / ISO 26262 pre-certified FreeRTOS-alike | Cost; API subset |
| **Embassy** (Rust) | Community | MIT/Apache | tiny | async/await, no thread stacks, integrated HALs | Rust-only; async debugging is different |
| **RTIC** (Rust) | Community | MIT/Apache | ~0 | Compile-time-verified resource locking (SRP), no scheduler overhead | Rust-only; different mental model |

**Current versions (Aug 2026):** Zephyr **4.4** (April 2026) is the latest stable, with
**v3.7 still the current LTS** and v4.6 planned as the next LTS in April 2027; Zephyr
moved to a 6-month April/October cadence. FreeRTOS **202604 LTS** (April 2026) ships
kernel **v11.3.0** with expanded MPU support and **coreMQTT v5.0.2 adding MQTT v5**
(topic aliases, request/response) — a notable catch-up.

**[CONTESTED] Zephyr vs FreeRTOS.** Both cases:
- *Zephyr*: you get a devicetree-described board, an in-tree driver for your sensor,
  a network stack, a settings/NVS subsystem, MCUboot integration, a shell, logging,
  power management, and a security process with CVE handling — as one coherent thing.
  For a connected product with a 10-year life and CRA obligations (§10.5 → `embedded-security-safety-and-testing`), the
  built-in SBOM/CVE and update story is a genuine risk reduction.
- *FreeRTOS*: you get a kernel you can read in an afternoon, MIT-licensed, with LTS and
  a paid Extended Maintenance Plan giving security patches for up to 10 more years —
  which matters enormously for products with 15-year field lives. You keep full control
  of your driver layer, and you're not exposed to another project's release churn.
- The honest framing: **Zephyr is an OS distribution; FreeRTOS is a scheduler.** Compare
  them at the same level or the comparison is meaningless. Zephyr's footprint advantage
  claims and FreeRTOS's "lightweight" claims have both shifted since ~2023 — evaluate on
  *your* build, not on blog posts.

### 2.4 Core RTOS concepts you must get right

**Scheduling**
- **Preemptive priority-based** is the default: highest-priority ready task runs.
- **Rate-monotonic (RMS)** assigns priority by *period*: shorter period → higher priority.
  For N independent periodic tasks with deadlines = periods, RMS is optimal among fixed-
  priority schemes, and the utilization bound is `U ≤ N(2^(1/N) − 1)` → 69.3% as N→∞.
  Below that bound, schedulability is *guaranteed*. Above it, you need **response-time
  analysis**: `R_i = C_i + Σ_{j∈hp(i)} ⌈R_i/T_j⌉ · C_j`, solved iteratively.
- **Time-slicing among equal priorities** is convenient and destroys determinism. In
  hard-real-time systems, give every task a unique priority.

**Priority inversion** [UNIVERSAL — memorize this]:
A low-priority task L holds a mutex. A high-priority task H blocks on it. A medium-
priority task M, needing nothing, preempts L. Now H waits on M — unbounded. This is
exactly what nearly killed Mars Pathfinder (§16 → `embedded-reference`).
- **Priority inheritance**: while H is blocked on L's mutex, L temporarily inherits H's
  priority. FreeRTOS mutexes (not semaphores!) do this. Zephyr mutexes do this.
- **Priority ceiling**: every mutex has a priority ≥ the highest of any task that takes
  it; a task taking it is raised immediately. Prevents deadlock too, at higher cost.
- **⚠️ GOTCHA**: a *binary semaphore* used for mutual exclusion gets you **no** priority
  inheritance. Use `xSemaphoreCreateMutex()` for locking, binary semaphores for signalling.
  This distinction is invisible until it's a field failure.

**Synchronization primitives — pick correctly**

| Need | Use | Do NOT use |
|---|---|---|
| Mutual exclusion | Mutex (with PI) | Binary semaphore, `taskENTER_CRITICAL` for long sections |
| ISR → task signal | Task notification (fastest) or binary semaphore | Queue for a bare event |
| ISR → task with data | Queue or stream/message buffer | Global variable + flag |
| Wait for N events | Event group / event flags | Polling |
| Producer/consumer bytes | Stream buffer (SPSC) | Queue of single bytes |
| Counting resources | Counting semaphore | Manual counter + mutex |

**FreeRTOS direct-to-task notifications** are ~45% faster and use less RAM than a binary
semaphore for the common ISR→single-task signalling case. Use them; most legacy code
doesn't.

**Tickless idle** stops the periodic tick during idle and reprograms a low-power timer to
wake at the next deadline. Without it, a 1 kHz tick wakes you 1000×/second and destroys
battery life. Enable it for any battery device (`configUSE_TICKLESS_IDLE`,
`CONFIG_PM` + `CONFIG_TICKLESS_KERNEL` in Zephyr) — then **verify with a current probe**,
because a single mis-configured peripheral clock keeps the whole domain awake.

**Stack overflow detection**: FreeRTOS `configCHECK_FOR_STACK_OVERFLOW = 2` (pattern
check) catches most cases at context-switch time. It is not free and it is not complete.
An **MPU stack guard** is the real answer.

### 2.5 Zephyr specifics worth knowing

**Devicetree** describes hardware declaratively; Kconfig configures software. They are
different systems and conflating them is the #1 beginner confusion.

```dts
/* Overlay: app.overlay — describe a sensor on I2C1 and an LED */
&i2c1 {
    status = "okay";
    clock-frequency = <I2C_BITRATE_FAST>;

    bme280@76 {
        compatible = "bosch,bme280";
        reg = <0x76>;
        status = "okay";
    };
};

/ {
    aliases {
        status-led = &led0;
    };
};
```
```c
#include <zephyr/device.h>
#include <zephyr/drivers/sensor.h>

/* Resolved at COMPILE time — no runtime string lookup, no null-name bugs */
static const struct device *const bme = DEVICE_DT_GET_ONE(bosch_bme280);
static const struct gpio_dt_spec led  = GPIO_DT_SPEC_GET(DT_ALIAS(status_led), gpios);

int main(void) {
    if (!device_is_ready(bme) || !gpio_is_ready_dt(&led)) return -ENODEV;
    gpio_pin_configure_dt(&led, GPIO_OUTPUT_ACTIVE);

    struct sensor_value temp;
    for (;;) {
        sensor_sample_fetch(bme);
        sensor_channel_get(bme, SENSOR_CHAN_AMBIENT_TEMP, &temp);
        printk("T=%d.%06d C\n", temp.val1, temp.val2);
        gpio_pin_toggle_dt(&led);
        k_sleep(K_SECONDS(1));
    }
}
```

Key Zephyr subsystems: **logging** (deferred, with backends), **shell** (invaluable for
bring-up and field diagnostics), **settings/NVS** (persistent config), **SMF** (state
machine framework), **power management** (device PM + system PM), **MCUboot** (secure
bootloader with swap/overwrite/DirectXIP modes), **west** (multi-repo manifest tool).

> **⚠️ GOTCHA — Zephyr version churn.** Migration guides exist between every release for a
> reason; APIs and Kconfig symbols move. For a product, pin to an LTS (currently v3.7) or
> to a vendor SDK that pins for you (nRF Connect SDK, Espressif's Zephyr port), and budget
> a deliberate upgrade project rather than tracking `main`.

### 2.6 Embedded Linux

**Build systems**
- **Yocto/OpenEmbedded**: recipes (`.bb`), layers (`meta-*`), BitBake. Produces a fully
  reproducible, license-audited, SBOM-capable distribution. Steep, slow, industry-standard
  for products. Current: **Yocto 6.0 "Wrynose" (May 2026), LTS through April 2030**, on
  Linux 6.18 LTS, GCC 15.2, glibc 2.43 — explicitly featuring improved SBOM and CVE
  tracking to ease EU CRA compliance.
- **Buildroot**: simpler, faster, `make menuconfig`-driven, no package manager on target.
  Excellent for fixed-function appliances. Weaker for multi-product line reuse.
- **Debian/Ubuntu-based**: fastest to start, hardest to make reproducible, biggest attack
  surface, worst for CRA-style lifecycle obligations. Fine for prototypes and internal
  tools; a liability for a shipped product.

**Boot chain**: ROM → SPL/TF-A (BL2/BL31) → **U-Boot** → kernel + **devicetree blob** →
init (systemd/BusyBox) → rootfs.

**Userspace hardware access — use the modern interfaces:**

| Need | Correct interface | Deprecated / wrong |
|---|---|---|
| GPIO | `libgpiod` v2 (`/dev/gpiochipN`) | `/sys/class/gpio` (removed) |
| SPI | `spidev` | bit-banging |
| I²C | `i2c-dev` | — |
| ADC/IMU/sensors | **IIO subsystem** (`/sys/bus/iio/...`, buffered mode w/ triggers) | raw `/dev/mem` |
| PWM | `sysfs pwm` or a proper driver | GPIO toggling from userspace |
| Any register poke | Write a kernel driver | `/dev/mem` (works, unsafe, unmaintainable) |

**Real-time on Linux**: **PREEMPT_RT was fully merged into mainline Linux 6.12
(September 2024)** for x86/x86_64, arm64, and RISC-V — the end of a ~20-year out-of-tree
effort. This removes the patch-maintenance burden but **does not** make Linux hard
real-time. What you get, tuned properly, is worst-case latencies in the tens of
microseconds instead of milliseconds.

To actually achieve it you need all of: `PREEMPT_RT` config, **CPU isolation**
(`isolcpus`, `nohz_full`, `rcu_nocbs`), IRQ affinity pinned off the isolated cores,
`SCHED_FIFO`/`SCHED_DEADLINE` for your RT threads, `mlockall(MCL_CURRENT|MCL_FUTURE)` to
prevent paging, no page faults in the hot path (pre-fault your stack and heap), disabled
CPU frequency scaling and C-states, and **measured proof** via `cyclictest` under
representative load (`stress-ng`, plus your actual I/O). Publish the histogram; a max
latency number without load context is meaningless.

**Update strategies for Linux devices** — pick one and design for it from day one:
- **A/B (dual-bank) rootfs**: RAUC, SWUpdate, Mender. Atomic, rollback-capable, costs 2×
  rootfs storage. The default recommendation.
- **OSTree / ostree-based** (e.g. Torizon, balena): git-like content-addressed filesystem
  trees, deduplicated, atomic. Efficient for frequent updates.
- **Container-based** (balena, Greengrass components): update apps without touching the OS.
  Doesn't solve kernel/BSP updates — you still need one of the above underneath.
- **Read-only rootfs + OverlayFS** for the writable parts is orthogonal and always a good
  idea: it makes power-loss corruption a non-event and makes the device's state auditable.

### 2.7 Toolchain

- **`arm-none-eabi-gcc`** remains the default; **LLVM/Clang** for embedded Arm and RISC-V
  is now fully viable and gives better diagnostics and `clang-tidy` integration.
- **C libraries**: `newlib` (full, large) → `newlib-nano` (smaller, no full printf float
  by default) → **`picolibc`** (modern, small, thread-local-storage-aware; ESP-IDF v6.0
  switched to it, Zephyr uses it). Choose picolibc for new work.
- **Size flags that always pay**: `-ffunction-sections -fdata-sections` +
  `-Wl,--gc-sections`, `-Os` (or `-Oz` on Clang), and **`-Wl,-Map=out.map`** always on.
- **LTO** (`-flto`) typically buys 5–15% size. It also makes debugging harder, can expose
  latent UB (the optimizer suddenly sees across TUs), and interacts badly with code that
  relies on a symbol being emitted. **⚠️ GOTCHA:** LTO will delete a variable that is
  written but never read — including one that only the debugger or a DMA engine reads.
  Mark such things `volatile` or `__attribute__((used))`.
- **Optimization vs debuggability**: build with `-Og -g3` during development. Debugging
  `-O2` code with variables "optimized out" wastes more time than the speed saves.
  **But**: always test at your release optimization level too, because timing and UB
  behaviour differ. Race conditions that only appear at `-O2` are real bugs, not compiler
  bugs, ~99% of the time.
- **Reproducible builds**: `-ffile-prefix-map`, `SOURCE_DATE_EPOCH`, pinned container
  images. Under CRA/SBOM regimes this stops being a nicety.
