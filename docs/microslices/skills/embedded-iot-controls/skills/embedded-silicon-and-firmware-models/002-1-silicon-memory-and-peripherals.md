---
id: skill-1-silicon-memory-and-peripherals-73dbb370c6
purpose: 1 silicon memory and peripherals
source: src/vibey_tools/skills/plugins/embedded-iot-controls/skills/embedded-silicon-and-firmware-models/SKILL.md
requires: ["skill-0-routing-what-kind-of-problem-is-this-70b909b916"]
links: ["skill-2-firmware-programming-models-8ca77c9d31"]
---

## §1. Silicon, Memory, and Peripherals

### 1.1 Core architectures — what actually differs

**Arm Cortex-M family [VENDOR, but near-universal in practice]**

| Core | ISA | Key features | Typical use |
|---|---|---|---|
| M0 / M0+ | ARMv6-M | 2-stage/3-stage pipe, no bit-banding on M0, MPU optional on M0+ | Ultra-low-power, cost-sensitive |
| M3 | ARMv7-M | Bit-banding, hardware divide, DWT/ITM | Legacy general purpose |
| M4 / M4F | ARMv7E-M | DSP (SIMD, MAC), optional single-precision FPU | Motor control, sensor fusion |
| M7 | ARMv7E-M | 6-stage superscalar, I/D caches, TCM, dual-issue | High-throughput control, DSP |
| M33 | ARMv8-M Mainline | **TrustZone-M**, DSP, FPU, stack limit registers | Secure connected devices — the modern default |
| M55 / M85 | ARMv8.1-M | **Helium (MVE)** vector extension, M85 adds PACBTI | On-device ML, DSP-heavy |
| M23 | ARMv8-M Baseline | TrustZone-M, low gate count | Secure + tiny |

**Critical M-profile facts [UNIVERSAL within Arm]:**
- Two stacks: **MSP** (Main Stack Pointer, used by handler mode and by thread mode after
  reset) and **PSP** (Process Stack Pointer). Every RTOS uses PSP for tasks and MSP for
  ISRs. `CONTROL[1]` selects.
- **Exception entry pushes 8 registers automatically** (R0–R3, R12, LR, PC, xPSR) — plus
  S0–S15 and FPSCR if lazy FP stacking is triggered. This is why an ISR's stack usage is
  never zero and why FPU-in-ISR blows stacks.
- **EXC_RETURN** in LR on exception entry is a magic value (0xFFFFFFxx) encoding which
  stack was in use and whether FP state was stacked. Decoding it is step 1 of any
  HardFault post-mortem (§5.8 → `embedded-languages-realtime-and-patterns`).
- **Tail-chaining**: back-to-back exceptions skip the pop/push, ~6 cycles instead of ~26.
- **Late arrival**: a higher-priority exception arriving during stacking preempts before
  the first handler runs.
- **Priority numbers are inverted**: lower number = higher priority. This trips up
  everyone once.
- Only the **upper N bits** of the 8-bit priority field are implemented (typically 3–4 →
  8 or 16 levels). `NVIC_SetPriority()` handles the shift; raw register writes usually
  don't.

> **⚠️ GOTCHA — priority grouping.** `AIRCR.PRIGROUP` splits priority into *preempt* and
> *sub-priority* fields. Sub-priority only breaks ties for simultaneous pending
> exceptions; it does **not** allow preemption. Configure all bits as preempt priority
> (PRIGROUP=0 on most parts) unless you have a specific reason. FreeRTOS on Cortex-M
> asserts on this in `configASSERT` if you build with `configASSERT` enabled — do that.

> **⚠️ GOTCHA — `configMAX_SYSCALL_INTERRUPT_PRIORITY`.** On Cortex-M, FreeRTOS masks
> interrupts with BASEPRI, not PRIMASK. Any ISR at a priority *numerically lower* (i.e.
> higher urgency) than `configMAX_SYSCALL_INTERRUPT_PRIORITY` is **never masked** and
> therefore **must not call any FreeRTOS API**, even `...FromISR` variants. Doing so
> corrupts kernel state non-deterministically. This is the single most common FreeRTOS
> bug in the wild.

**Cortex-A / MPU-class**: MMU with virtual memory, multiple privilege levels (EL0–EL3),
caches with coherency concerns, GIC instead of NVIC, and boot via ROM → SPL/TF-A → U-Boot
→ kernel. Determinism is fundamentally worse: cache misses, TLB misses, DVFS, and SMP
migration all inject jitter.

**RISC-V** is now genuinely mainstream in commercial MCUs, not a curiosity. Espressif's
entire modern line is RISC-V (C3/C5/C6/C61/H2/H4/P4); the ESP32-P4 is dual-core RISC-V at
400 MHz with 768 KB SRAM and no radio (pair it with a C6 for connectivity). RP2350 ships
*both* Cortex-M33 and RISC-V Hazard3 cores on the same die. Key differences from Arm:
- **PLIC/CLIC** instead of NVIC; interrupt handling is less standardized across vendors.
- No architecturally mandated exception stacking — the compiler/runtime does it, so
  ISR entry cost varies by toolchain.
- Privilege modes M/S/U; embedded parts are usually M-mode only.
- Extensions matter enormously: `RV32IMAC` vs `RV32IMAFC` vs vector `V`. "RISC-V" alone
  tells you almost nothing about capability.

**Xtensa** (classic ESP32, S2, S3) — windowed register file, which makes stack unwinding
and backtraces genuinely harder. Espressif is migrating to RISC-V; new designs should
default to RISC-V parts unless you need S3's specific vector DSP.

**AVR / MSP430 / PIC** — still shipping in enormous volume where BOM cost is king.
MSP430's FRAM variants are notable: non-volatile at SRAM speed, unlimited-ish write
endurance, and no separate flash-erase step. That changes your data-logging architecture
completely.

### 1.2 Memory architecture — the part that bites

**Section layout** (what your linker script actually produces):

| Section | Contents | Lives in | Initialized by |
|---|---|---|---|
| `.text` | Code | Flash | — |
| `.rodata` | `const` data, string literals | Flash | — |
| `.data` | Initialized globals/statics | RAM (copy in Flash) | startup: memcpy from LMA→VMA |
| `.bss` | Zero-initialized globals/statics | RAM | startup: memset 0 |
| `.noinit` | Data surviving reset | RAM | nothing (deliberately) |
| heap | `malloc` arena | RAM | grows up |
| stack | Automatic variables, ISR frames | RAM | grows **down** on Arm |

**[UNIVERSAL] Read the `.map` file.** It is the ground truth for "why doesn't it fit"
and "what pulled in 12 KB of printf float formatting." `arm-none-eabi-size` gives you
the summary; `nm --size-sort -S` gives you the offenders; `--print-memory-usage` (GCC)
gives you percentages per region.

**Stack sizing [UNIVERSAL]:** you cannot compute it by inspection in the presence of
recursion, function pointers, or vendor blobs. Use all three of:
1. Static analysis (`-fstack-usage` + a call-graph tool, or GCC's `.su` files) for a
   worst-case bound on the code you control.
2. **Stack painting**: fill the stack with a pattern (0xA5A5A5A5) at boot, then read the
   high-water mark at runtime. FreeRTOS gives you `uxTaskGetStackHighWaterMark()`; Zephyr
   gives you `CONFIG_THREAD_ANALYZER`.
3. An **MPU guard region** below each stack so overflow faults instead of silently
   corrupting the neighbouring task. This is the only mechanism that turns a
   heisenbug into a reproducible fault.

> **⚠️ GOTCHA — heap in embedded.** `malloc()` is not forbidden by physics; it is
> forbidden by *fragmentation* and *non-determinism*. If you must allocate dynamically,
> allocate **once at init and never free** (this is fine and common), or use fixed-block
> pools (§5.4 → `embedded-languages-realtime-and-patterns`). MISRA C:2012 Dir 4.12 / Rule 21.3 ban dynamic allocation outright for
> exactly this reason.

**Cortex-M7 cache + DMA — the classic silent data corruption [VENDOR, high-frequency]:**
The M7 has separate I-cache and D-cache and **no hardware coherency with DMA**. Symptoms:
DMA-received data looks stale; DMA-transmitted data is garbage or old.

- **DMA writes to memory (RX)**: CPU may hold a stale cache line. You must
  `SCB_InvalidateDCache_by_Addr()` **after** the transfer completes and **before** reading.
- **CPU writes to memory, DMA reads (TX)**: data may still be in cache. You must
  `SCB_CleanDCache_by_Addr()` **before** starting the DMA.
- Cache maintenance operates on **32-byte lines**. If your buffer isn't 32-byte-aligned
  and a multiple of 32 bytes, you will invalidate a neighbouring variable and corrupt it.
  Align every DMA buffer: `__attribute__((aligned(32)))`.
- The clean alternative: put DMA buffers in a **non-cacheable MPU region**, or in
  **DTCM** (tightly-coupled memory), which is not cached at all. This is what most
  shipping STM32H7 designs do, and it is the recommendation.

**Memory technologies:**

| Type | Endurance | Write speed | Byte-writable | Notes |
|---|---|---|---|---|
| NOR Flash (internal) | 10k–100k cycles | slow (ms erase) | No — erase sector first | Execute-in-place; erase granularity is the design constraint |
| NAND Flash (external) | 1k–100k | fast page write | No | Needs FTL + bad-block management; use a proper FS (UBIFS, littlefs) |
| EEPROM | ~1M | slow | Yes | Config storage; often emulated in flash on modern MCUs |
| FRAM | ~10^14 | SRAM-speed | Yes | No erase cycle; excellent for logging and power-fail-safe writes |
| SRAM | ∞ | fastest | Yes | Volatile; the scarce resource |
| External PSRAM (QSPI/OSPI) | ∞ | slow-ish, cached | Yes | ESP32-S3/P4, STM32H7; watch latency in real-time paths |

> **⚠️ GOTCHA — flash wear and power loss.** Config stored as "erase sector, write new
> record" is not power-fail-safe. Use a journaling/log-structured scheme: **littlefs**
> (MCU-class, power-loss resilient, wear-levelling) or **NVS** (Zephyr settings / ESP-IDF
> NVS). Rolling your own EEPROM emulation is a rite of passage that ends in field returns.

### 1.3 Clocks, reset, and boot

**Clock tree** [UNIVERSAL pattern, VENDOR specifics]: source (HSI internal RC / HSE
crystal / LSE 32.768 kHz) → PLL(s) → system clock → prescalers → bus clocks (AHB, APB1,
APB2) → peripheral clocks.

- Internal RC oscillators are typically **±1–2%** over temperature — fine for a UART at
  9600 with autobaud, **not** fine for CAN, USB, or a UART at 1 Mbaud. USB needs ≤0.25%;
  CAN needs the bit-timing error budget to close.
- Every peripheral has a **clock enable bit**. Writing a peripheral register with its
  clock gated silently does nothing (or hard-faults on some parts). This is the #1
  "my GPIO doesn't work" cause.
- After enabling a peripheral clock on many STM32 parts you must insert a **dummy read
  back** of the RCC register — the write is posted and the peripheral isn't ready for a
  cycle or two. Vendor HALs do this; hand-rolled register code often doesn't.

**Boot sequence [UNIVERSAL for Cortex-M]:**
1. Power-on reset releases; core reads **address 0x00000000** → initial MSP value.
2. Reads **0x00000004** → reset vector (address of `Reset_Handler`), sets PC.
3. `Reset_Handler` (in `startup_xx.s`): optionally sets up clocks/FPU (`SystemInit`),
   copies `.data` from LMA to VMA, zeroes `.bss`, runs C++ static constructors
   (`__libc_init_array`), calls `main()`.
4. `main()` never returns; if it does, an infinite loop catches it.

On parts with a ROM bootloader (nearly all modern ones), a **BOOT pin / option byte /
strapping** decides whether the ROM runs a DFU/UART/USB loader instead. Know how to force
this — it is your recovery path when you brick an OTA.

**Reset reason is free forensics.** Every MCU latches why it reset (POR, BOR, watchdog,
software, pin, low-power exit). Read it at boot, log it, and ship it to your fleet
telemetry (§9.4 → `embedded-industrial-control-connectivity-and-cloud`). A fleet-wide spike in watchdog resets is the earliest signal of a
firmware regression you will get.

### 1.4 Interrupts and the interrupt discipline

**[UNIVERSAL] The three rules of ISRs:**
1. **Short.** An ISR should acknowledge the hardware, move data, and signal. Microseconds,
   not milliseconds.
2. **Non-blocking.** No mutexes, no `malloc`, no `printf`, no waiting on anything.
3. **Deferred work.** Real processing happens in a task (bottom half). The ISR posts to a
   queue / gives a semaphore / sets a task notification and returns.

**Latency budget** = (longest critical section anywhere in the system) + (higher-priority
ISR execution time) + (exception entry ~12–26 cycles) + (handler prologue). The dominant
term is almost always **your own critical sections** — which is why "disable interrupts
for the whole function" is a real-time bug even when it's not a correctness bug.

**Nested interrupts** are supported on Cortex-M by default. This is good (low latency for
urgent sources) and dangerous (each nesting level costs stack). Budget stack for the
maximum nesting depth × frame size.

> **⚠️ GOTCHA — the spurious/lost interrupt.** On many peripherals, clearing the interrupt
> flag is a *write-1-to-clear* to a status register. If you clear the flag at the **end**
> of a long ISR, a second event arriving mid-ISR is silently lost. Clear **early**, then
> process. Conversely, on some parts the flag clear is posted and the ISR re-enters
> because the NVIC hasn't seen the deassert yet — insert a read-back (`__DSB()`) before
> returning. Both failure modes exist; check the reference manual, not your intuition.

### 1.5 Peripherals — the specifics that matter

**GPIO**
- **Push-pull** (drives both rails) vs **open-drain** (pulls low, needs external pull-up —
  required for I²C and any wired-AND bus).
- Internal pull-ups are typically **30–50 kΩ** — far too weak for I²C at 400 kHz with any
  bus capacitance. Use external 2.2–4.7 kΩ.
- **Slew rate / drive strength** settings exist for EMI reasons. Fastest slew on a long
  trace radiates. If your product fails EMC pre-compliance, reducing GPIO slew rate and
  enabling spread-spectrum clocking are the two cheapest firmware fixes.
- **Alternate function** muxing: a pin can be GPIO, or SPI1_SCK, or TIM3_CH1... Getting
  the AF number wrong produces a pin that reads as input-floating and no error message.

**Timers**
- **PWM**: period = ARR (auto-reload), duty = CCR (capture/compare). Resolution =
  log2(ARR). At 100 kHz PWM from a 100 MHz clock you get ARR=1000 → ~10 bits. There is a
  hard trade between PWM frequency and duty resolution. This bites motor control and
  Class-D audio.
- **Dead-time insertion** on advanced timers (TIM1/TIM8 on STM32) is mandatory for
  half-bridge drive — without it, shoot-through destroys the FETs. Set it in hardware, not
  software.
- **Input capture** timestamps an edge in hardware — the only accurate way to measure
  pulse width, frequency, or do ultrasonic ToF. Software GPIO polling has jitter equal to
  your loop period.
- **Encoder mode** decodes quadrature in hardware, giving you a free position counter with
  4× resolution and no missed counts. Never bit-bang quadrature above a few kHz.

**ADC**
- **SAR** (successive approximation): fast (µs), moderate resolution (12–16 bit), the
  MCU default. **Sigma-delta**: slow, very high resolution (24 bit), used for weigh scales
  and precision instrumentation.
- **Sampling time** is not optional tuning: the internal sample-and-hold capacitor must
  charge through your source impedance. Rule of thumb: sampling time ≥ 10 × R_source ×
  C_sample. A 100 kΩ divider into a 5-cycle sample time gives you readings that are simply
  wrong, and they'll be *consistently* wrong so they look plausible.
- **ENOB** (effective number of bits) is always less than the marketed resolution. A
  "12-bit ADC" on a noisy board with a poor reference is a 9-bit ADC.
- **Oversampling and decimation**: averaging 4^N samples buys N bits of resolution
  *if and only if* there is at least 1 LSB of noise to dither with. Many MCUs do this in
  hardware for free.
- **Reference selection** dominates absolute accuracy. VDD-as-reference means your reading
  moves with your supply. Ratiometric sensing (sensor and ADC share the reference) cancels
  this — use it wherever the sensor is a resistive divider.

**Watchdogs**
- **Independent watchdog (IWDG)** runs from its own LSI oscillator and cannot be stopped
  by software once enabled. This is the one that saves you.
- **Window watchdog (WWDG)** faults if you kick too *early* as well as too late — catches
  runaway loops that happen to include a kick.
- **[UNIVERSAL] Never kick the watchdog from a timer ISR or a dedicated "kicker" task.**
  That defeats the purpose: it proves only that interrupts still work. The correct pattern
  is a **supervised watchdog**: each critical task sets a bit/heartbeat; a single low-rate
  supervisor verifies *all* bits are set within their deadlines and only then kicks.
  See §5.9 → `embedded-languages-realtime-and-patterns` for code.

**Buses — the comparison**

| Bus | Wires | Typical rate | Topology | Addressing | Failure modes to know |
|---|---|---|---|---|---|
| UART | 2 (+2 flow) | ≤ 12 Mbaud | Point-to-point | none | Baud error >2% → framing errors; no clock recovery |
| RS-485 | 2 (differential) | ≤ 10 Mbps | Multi-drop | protocol-level | Termination, biasing, DE turnaround timing |
| SPI | 4 (+1/CS) | ≤ 100 MHz | Star (per-CS) | chip select | CPOL/CPHA mismatch = garbage; no ack, no error detection |
| I²C | 2 (open-drain) | 100k/400k/1M/3.4M | Multi-drop | 7 or 10-bit | Bus lockup, clock stretching, pull-up sizing, address collisions |
| I3C | 2 | ≤ 12.5 Mbps | Multi-drop | dynamic | Backward-compatible with I²C; still thin ecosystem |
| CAN / CAN-FD | 2 (differential) | 1 Mbps / 8 Mbps data | Multi-drop | 11/29-bit ID arbitration | Bit timing/sample point, bus-off recovery, no addressing (content-based) |
| 1-Wire | 1 (+GND) | ~16 kbps | Multi-drop | 64-bit ROM ID | Timing-critical bit-banging; parasitic power |
| USB | 2 (differential) | 12/480 Mbps+ | Star (hub) | enumerated | Descriptor bugs, clock accuracy, host stack variability |
| Ethernet (RMII/MII) | 4/16 + MDIO | 10/100/1000 | Star | MAC/IP | PHY strapping, clock direction (REF_CLK source), auto-negotiation |

> **⚠️ GOTCHA — I²C bus lockup.** If the MCU resets mid-transaction while a slave is
> driving SDA low, the bus is stuck forever and every subsequent transaction times out.
> **Recovery, at every boot, before initializing the I²C peripheral:** configure SCL/SDA
> as GPIO open-drain, clock SCL 9–16 times while SDA is released, then issue a manual
> STOP condition (SDA low→high while SCL high), then hand the pins back to the I²C
> peripheral. Ship this. It costs 30 lines and eliminates a whole class of field returns.

> **⚠️ GOTCHA — CAN sample point.** Every node on a CAN bus must agree on the bit timing
> *sample point* (typically 75–87.5% of the bit, per CiA recommendations), not just the
> bitrate. Two nodes at "500 kbps" with different sample points will work on the bench and
> fail intermittently on a long harness at temperature. Use a bit-timing calculator; record
> the tq/BRP/TSEG1/TSEG2 values in your design docs.

> **⚠️ GOTCHA — SPI mode.** CPOL (idle clock level) and CPHA (sample on first or second
> edge) give four modes. Datasheets describe them inconsistently ("mode 3" vs
> "CPOL=1, CPHA=1" vs a timing diagram). When a new SPI device returns 0x00 or 0xFF
> forever, try all four modes before debugging anything else. It takes 2 minutes and is
> right more often than it should be.

### 1.6 Power — the discipline that decides battery life

**[UNIVERSAL] Energy per operation, not current draw, is the design metric.**
`E = ∫ V·I dt`. A part that draws 20 mA for 2 ms beats one that draws 5 mA for 20 ms.

**Sleep-mode taxonomy** (names vary; behaviour doesn't):

| Mode | CPU | RAM | Peripherals | Wake sources | Typical current | Wake time |
|---|---|---|---|---|---|---|
| Run | on | on | on | — | mA–tens of mA | — |
| Sleep / WFI | clock-gated | on | on | any interrupt | ~30–50% of run | ~cycles |
| Stop / Deep-sleep | off | retained | few (RTC, LPUART) | RTC, pin, LPUART | 1–10 µA | 5–100 µs |
| Standby / Hibernate | off | **lost** (except backup) | RTC only | RTC, wake pin | 0.1–1 µA | ms (full reboot) |
| Shutdown / Off | off | lost | none | pin only | ~10–100 nA | full reboot |

**The battery-life calculation that actually predicts reality:**
```
Q_total = Σ over each state ( I_state × t_state ) per duty cycle
        + self-discharge (2–3 %/yr for lithium primary, much worse for LiPo)
        + quiescent current of every regulator, level shifter, and pull-up on the board
```
That last term kills more designs than firmware does. A single 10 kΩ pull-up tied to 3.3 V
through a closed switch is 330 µA — more than your entire sleeping MCU.

> **⚠️ GOTCHA — coin cell peak current.** A CR2032 has an internal resistance that rises
> from ~10 Ω new to >100 Ω at end of life and at cold temperature. A BLE transmit burst
> of 15 mA causes a voltage droop that browns out the MCU — the cell has capacity left,
> but the device resets. **Fix:** a bulk capacitor (10–100 µF ceramic/tantalum) across the
> cell, plus firmware that staggers radio TX and flash writes so they never overlap.
> Model this before you build 10,000 units.

> **⚠️ GOTCHA — GPIO state in sleep.** Floating inputs in deep sleep oscillate and burn
> µA each. Before entering deep sleep, configure every unused pin as analog or with a
> defined pull. Vendor low-power app notes exist for this; read them (ST AN4899, Nordic's
> power optimization guide, TI's ULP advisor).

### 1.7 What firmware engineers must know about hardware

- **Decoupling**: every VDD pin gets a 100 nF close to the pin plus bulk. If you're
  debugging "random resets", scope VDD at the pin with a 20 MHz-bandwidth-limited probe
  before you touch code.
- **Brown-out detection (BOR)**: enable it, set the threshold above the MCU's minimum
  operating voltage, and check the reset reason. Undervoltage operation causes flash
  corruption and impossible-looking bugs.
- **ESD and floating inputs**: an unconnected input on a connector is an antenna.
- **EMC is partly a firmware problem**: slew rate, spread-spectrum clocking, PWM edge
  alignment, and not toggling a GPIO at exactly the frequency the test antenna is
  scanning.
- **Power sequencing**: many SoCs require rails to come up in order. If your board violates
  this, you get intermittent boot failures that look like software.

---
