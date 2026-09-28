---
id: skill-3-languages-737593fbec
purpose: 3 languages
source: src/vibey_tools/skills/plugins/embedded-iot-controls/skills/embedded-languages-realtime-and-patterns/SKILL.md
requires: []
links: ["skill-4-concurrency-timing-and-real-time-correctness-0b441e02f0"]
---

## §3. Languages

### 3.1 The honest comparison

| | C | C++ (subset) | Rust | MicroPython | Ada/SPARK |
|---|---|---|---|---|---|
| Smallest viable target | ~2 KB | ~4 KB | ~4 KB | ~256 KB | ~8 KB |
| Memory safety | none | partial (RAII) | **compile-time** | runtime (GC) | strong + provable |
| Certified toolchain | many | many | **Ferrocene** | none | many |
| Ecosystem breadth | vast (vendor) | vast | good & growing | modest | narrow |
| Hiring pool | huge | large | small but growing | large | tiny |
| Determinism | full | full (w/o exceptions/heap) | full | **no (GC pauses)** | full |
| Best for | anything, esp. legacy & certified | large firmware needing abstraction | new safety/security-critical work | prototyping, education, non-RT | highest-integrity |

### 3.2 C — the lingua franca, and its traps

**Fixed-width types always.** `#include <stdint.h>`; `int` is 16-bit on some targets and
32-bit on others.

**Integer promotion is the #1 silent C bug in embedded code:**
```c
uint8_t  a = 200, b = 100;
uint8_t  c = a + b;              /* a,b promoted to int; 300 truncated to 44 */
uint16_t x = 0xFFFF;
uint32_t y = x << 16;            /* x promoted to int(32); if int is 16-bit → UB */
if (some_uint8 << 8 > 1000) ...  /* promotion + precedence trap */
```
Rule: cast explicitly at every point where width matters. `(uint32_t)x << 16`.

**Signed overflow is undefined behaviour**, and modern compilers exploit it aggressively
(`if (x + 1 < x)` gets optimized to `false`). Unsigned overflow is defined (wraps). Use
unsigned for counters and rely on it deliberately (§5.5).

**`volatile` means "the compiler must not cache or reorder *this* access."** It does
**not** mean atomic, and it does **not** create a memory barrier for other accesses.
Every memory-mapped register must be `volatile` (CMSIS headers do this). Every variable
shared between an ISR and a task must be `volatile` **and** accessed atomically (§4.3).
Using `volatile` as a substitute for a lock is a bug that works until it doesn't.

**Strict aliasing**: accessing an object through a pointer of an incompatible type is UB.
The classic float↔uint32 bit-punning via pointer cast is UB; use `memcpy` (the compiler
optimizes it away) or a `union` (well-defined in C, implementation-defined in C++).

**MISRA C** — current version is **MISRA C:2025** (published March 2025), an incremental
update to **MISRA C:2023** (April 2023), which itself consolidated MISRA C:2012 plus
Amendments 1–4 and TC2. Coverage is C90/C99/C11/C18; roughly 225 active guidelines.
Amendment 4's Rules 22.11–22.20 added **concurrency and atomics guidance** — the first
formal MISRA coverage of multi-threaded C, which matters now that multicore MCUs are
common. **MISRA C++:2023** (October 2023) targets C++17, defines ~179 rules, and **merged
AUTOSAR C++14 into MISRA** — so "AUTOSAR C++14" as a separate standard is effectively
superseded. A new MISRA C++ is in development with no announced date.

Practical MISRA advice: **adopt it as a static-analysis ruleset with documented deviations,
not as gospel.** The deviation process is part of the standard. Teams that treat every
rule as mandatory produce worse code (e.g. banning all `goto` when the single-exit
cleanup `goto` pattern is clearer than nested flags).

**Useful C idioms in embedded:**
```c
/* X-macros: one list, many derived artifacts — no drift between table and enum */
#define SENSOR_LIST(X)            \
    X(TEMP,   0x01, temp_read)    \
    X(HUMID,  0x02, humid_read)   \
    X(PRESS,  0x04, press_read)

typedef enum { 
#define X(name, mask, fn) SENSOR_##name,
    SENSOR_LIST(X)
#undef X
    SENSOR_COUNT
} sensor_id_t;

static const sensor_desc_t sensors[SENSOR_COUNT] = {
#define X(name, mask, fn) [SENSOR_##name] = { .mask = (mask), .read = (fn) },
    SENSOR_LIST(X)
#undef X
};

/* Compile-time assertions — catch layout/config errors at build, not at 3am */
_Static_assert(sizeof(protocol_frame_t) == 16, "frame packing changed");
_Static_assert((TICK_HZ % CONTROL_HZ) == 0,    "control rate must divide tick rate");
```

### 3.3 C++ in embedded — the safe subset

**Zero-cost and worth using:**
- `constexpr` / `consteval` — move computation to compile time (CRC tables, lookup tables,
  unit conversions). This is C++'s single biggest embedded win.
- `enum class` — no implicit int conversion, no namespace pollution.
- `std::array<T,N>` — same layout as a C array, with `.size()` and bounds-checked `.at()`.
- **RAII** — deterministic cleanup for locks, DMA channels, chip-select assertions. Reduces
  a whole class of "forgot to release" bugs to zero.
- Templates for **static polymorphism** (CRTP) — dispatch resolved at compile time, no
  vtable, fully inlinable.
- **Strong types** — `struct Millivolts { int32_t v; };` prevents the unit-mixing errors
  that destroyed the Mars Climate Orbiter.
- `[[nodiscard]]` on every function returning an error code.

**Costly / banned in most embedded shops:**
- **Exceptions** — table-based unwinding costs flash even unused (link `-fno-exceptions`),
  and throw/catch timing is unbounded. Nearly universally disabled.
- **RTTI / `dynamic_cast`** — `-fno-rtti`.
- **`iostream`** — pulls in tens of KB. Use `printf`, or better, a binary logger (§12.5 → `embedded-security-safety-and-testing`).
- **Heap-based STL** (`std::vector`, `std::string`, `std::function`, `std::map`) — dynamic
  allocation and unbounded latency. Use **ETL (Embedded Template Library)** for
  fixed-capacity equivalents, or `etl::delegate`/function-pointer for callbacks.

**Standard build flags for embedded C++:**
`-fno-exceptions -fno-rtti -fno-threadsafe-statics -fno-use-cxa-atexit`
(the last two remove hidden guards/registration on static locals and destructors).

```cpp
/* CRTP static polymorphism — polymorphic interface, zero vtable, fully inlined */
template <typename Impl>
class SensorBase {
public:
    int32_t read() { return static_cast<Impl*>(this)->read_impl(); }
};

class Bme280 : public SensorBase<Bme280> {
    friend class SensorBase<Bme280>;
    int32_t read_impl() { /* register access */ return 0; }
};

/* Compile-time-safe register access — wrong-width writes fail to compile */
template <uintptr_t Addr, typename T = uint32_t>
struct Reg {
    static T  read()          { return *reinterpret_cast<volatile T*>(Addr); }
    static void write(T v)    { *reinterpret_cast<volatile T*>(Addr) = v; }
    static void set(T mask)   { write(read() |  mask); }
    static void clear(T mask) { write(read() & ~mask); }
};
```

### 3.4 Rust in embedded — where it actually stands in 2026

**The ecosystem is no longer experimental.** Key facts as of 2026:
- **`embedded-hal` 1.0 is released and stable**, giving the driver ecosystem a
  semver-stable trait foundation (both blocking and async variants). Hundreds of
  platform-agnostic sensor/peripheral driver crates build on it.
- **Embassy** is the de-facto async runtime, with first-party HALs for STM32 (all
  families), nRF (52/53/54/91), RP2040/RP235x, TI MSPM0, NXP MCX-A, plus `esp-hal` and
  `ch32-hal` from their respective communities. Embassy compiles on **stable Rust** since
  1.75.
- **RTIC** remains the choice when you want a pure execution framework with
  compile-time-verified resource locking (Stack Resource Policy) and no runtime.
- **`probe-rs`** has effectively displaced OpenOCD for Rust workflows (and works fine for
  C too); **`defmt`** gives deferred, format-string-interned logging that is dramatically
  cheaper than `printf`.
- **Espressif has elevated `esp-rs` to a top-tier official SDK** for its RISC-V line.
- **Ferrocene** (Ferrous Systems) is the qualified toolchain: **TÜV SÜD-qualified for
  ISO 26262 ASIL D, IEC 61508 SIL 3 (supporting customer efforts to SIL 4), and IEC 62304
  Class C**, with a **certified subset of `core` at IEC 61508 SIL 2 / ISO 26262 ASIL B**
  (a critical 2025–26 milestone, since `no_std` Rust is unusable without `core`). Targets
  include Linux, QNX Neutrino, and bare-metal Armv8-A and **Armv7E-M**.

**The layering** (learn these four words, they explain everything):
```
PAC   — Peripheral Access Crate. Auto-generated from the vendor SVD by svd2rust.
        Raw registers, but type-safe field access. e.g. stm32f4
HAL   — Hardware Abstraction Layer. Ergonomic drivers implementing embedded-hal traits.
        e.g. stm32f4xx-hal, embassy-stm32, esp-hal
BSP   — Board Support Package. Named pins/peripherals for a specific board.
Driver— Platform-agnostic device crate, generic over embedded-hal traits.
```

**The typestate pattern** — Rust's genuinely novel embedded contribution. Peripheral
configuration is encoded in the *type*, so misuse fails at compile time:
```rust
// A pin configured as Input cannot be written to — this is a compile error, not a bug.
let gpioa = dp.GPIOA.split();
let mut led   = gpioa.pa5.into_push_pull_output();   // Pin<'A',5, Output<PushPull>>
let     button = gpioa.pa0.into_pull_up_input();     // Pin<'A',0, Input<PullUp>>

led.set_high().unwrap();
// button.set_high();  // ← does not compile: no such method on an Input pin

// Ownership prevents two drivers silently sharing a peripheral:
let spi = Spi::new(dp.SPI1, (sck, miso, mosi), MODE_0, 1.MHz(), &clocks);
let display = Display::new(spi, dc_pin, cs_pin);      // spi is MOVED
// let other = OtherDriver::new(spi);  // ← does not compile: spi already moved
```
```rust
// Embassy: concurrency without thread stacks. Each task is a state machine
// sized at compile time; no per-task stack allocation.
#[embassy_executor::task]
async fn blinker(mut led: Output<'static>, interval: Duration) {
    loop {
        led.toggle();
        Timer::after(interval).await;     // yields; zero CPU while waiting
    }
}

#[embassy_executor::main]
async fn main(spawner: Spawner) {
    let p = embassy_stm32::init(Default::default());
    let led = Output::new(p.PA5, Level::Low, Speed::Low);
    spawner.spawn(blinker(led, Duration::from_millis(500))).unwrap();
    // Other tasks run cooperatively on the same executor.
    // Multiple executors at different interrupt priorities give you preemption.
}
```

**[CONTESTED] Rust vs C for new embedded work.** Steelman both:
- *For Rust*: memory-safety bugs (buffer overflow, use-after-free, data race) are
  eliminated by construction — and these are the dominant CVE class in firmware.
  The typestate/ownership model catches whole categories of driver misuse at compile time.
  `cargo` dependency management beats copying vendor SDK zips. `defmt`+`probe-rs` is a
  better debug loop than most C toolchains. Ferrocene removes the "we can't certify it"
  objection.
- *For C*: the vendor ecosystem is C — every reference design, app note, errata
  workaround, silicon vendor driver, and third-party stack. Rust HAL coverage for a
  specific obscure part is often incomplete, and you end up writing `unsafe` PAC code
  anyway. Certified C toolchains, MISRA tooling, and static analyzers are mature and
  procurable. Your team already knows C, and hiring embedded Rust engineers is hard.
  Async Rust in safety contexts raises unresolved questions about qualifying the runtime.
- *The pragmatic middle*: Rust for new greenfield connected/security-sensitive products on
  well-supported parts (nRF, STM32, RP2350, ESP32-C/P); C for legacy, obscure silicon,
  and anything where the vendor stack is load-bearing. Mixed-language via FFI is normal.

### 3.5 Everything else

- **MicroPython / CircuitPython**: excellent for prototyping, teaching, and non-real-time
  glue on parts with ≥256 KB flash. **Not** for control loops (GC pauses are
  unbounded-ish) or for products needing sub-ms determinism. CircuitPython's driver library
  breadth is a genuine prototyping accelerator.
- **TinyGo**: LLVM-based Go for MCUs. Nice concurrency model; GC still present (though
  configurable); ecosystem thinner than Rust's.
- **Ada/SPARK**: the highest-assurance option. SPARK's provable absence of runtime errors
  is used in avionics and rail. Tiny talent pool; superb where it fits.
- **WebAssembly on MCUs** (WAMR, Wasm3, WASI): sandboxed, updatable application logic on
  top of native firmware. Real production use in edge/plugin architectures; costs
  interpretation overhead unless AOT-compiled.
- **Elixir/Nerves**: Linux-class devices where BEAM's supervision trees and hot-code
  loading suit long-lived fleet devices.
- **Lua (eLua/NodeMCU), JavaScript (Espruino, Moddable XS)**: scripting layers for
  configurable behaviour, useful when end users need to customize device logic.

---
