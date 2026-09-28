---
id: skill-12-testing-verification-and-debugging-534af92c27
purpose: 12 testing verification and debugging
source: src/vibey_tools/skills/plugins/embedded-iot-controls/skills/embedded-security-safety-and-testing/SKILL.md
requires: ["skill-11-functional-safety-37c9804c6f"]
links: ["skill-13-board-bring-up-03ee099e9a"]
---

## §12. Testing, Verification, and Debugging

### 12.1 The testing pyramid, embedded edition

```
        ▲  Field / fleet monitoring (§9.4)   ← the ultimate integration test
       ╱ ╲ HIL — real firmware, real MCU, simulated plant
      ╱   ╲ On-target integration — real hardware, real peripherals
     ╱     ╲ Simulation (Renode, QEMU, Wokwi) — full system, no hardware
    ╱       ╲ Host unit tests with fakes — milliseconds, run on every commit
   ╱_________╲ Static analysis + compiler warnings — run on every save
```
**[UNIVERSAL] The biggest single productivity lever in embedded software is being able to
run most of your tests on a host machine in under 10 seconds.** That requires the
hardware seam from §5.1 → `embedded-languages-realtime-and-patterns`. Teams without it have a 5-minute flash-and-observe loop and
consequently test far less.

### 12.2 Unit testing firmware

**Frameworks**: **Unity + CMock + Ceedling** (C, the classic embedded stack, generates
mocks from headers), **CppUTest** (C/C++, has a memory-leak detector), **GoogleTest**,
**Catch2**, **FFF** (Fake Function Framework — header-only C fakes, minimal ceremony).

**Dual-target build**: the same source compiles for the host (native, with fakes and
sanitizers) and for the target. Enables **ASan/UBSan/TSan on the host**, which find
memory bugs that are invisible on the target until they corrupt something three modules
away.

```c
/* Host test using FFF — no hardware, no vendor SDK, runs in ~1 ms */
#include "fff.h"
DEFINE_FFF_GLOBALS;
FAKE_VALUE_FUNC(int, i2c_write, void*, uint8_t, const uint8_t*, size_t);
FAKE_VALUE_FUNC(int, i2c_read,  void*, uint8_t,       uint8_t*, size_t);

static uint8_t canned[3] = { 0x7E, 0x8C, 0x00 };   /* datasheet's worked example */
static int read_canned(void *c, uint8_t a, uint8_t *d, size_t n) {
    memcpy(d, canned, n); return 0;
}

void test_temp_matches_datasheet_reference(void) {
    i2c_read_fake.custom_fake = read_canned;
    bme280_t dev = { .bus = &fake_bus, .addr = 0x76 };
    int32_t t;
    TEST_ASSERT_EQUAL(0, bme280_read_temp(&dev, &t));
    TEST_ASSERT_INT32_WITHIN(50, 25400, t);        /* 25.4 °C ± 0.05 */
    TEST_ASSERT_EQUAL(1, i2c_write_fake.call_count);
    TEST_ASSERT_EQUAL(0xFA, i2c_write_fake.arg2_history[0][0]);
}
```

**What to test on the host**: protocol parsers (feed them fuzzed input!), state machines
(every transition, including illegal ones), control algorithms (step response against
expected), data transformations, checksum/CRC, compensation math, ring buffers, and
anything with an if-statement. **What you cannot test on the host**: timing, ISR
interactions, actual peripheral behaviour, and silicon errata.

**Fuzzing**: compile your protocol parser for the host and run **libFuzzer** or **AFL++**
against it. Firmware parsers handle untrusted network input and are almost never fuzzed.
This is an unusually high return on a day's work.

**Property-based testing** (theft, RapidCheck, Hypothesis via a Python harness): assert
invariants (e.g. "pushing then popping a ring buffer returns the same bytes in order, for
any sequence of operations") and let the tool find the counterexample. Excellent for
buffers, encoders, and state machines.

### 12.3 Simulation and HIL

- **Renode** — the standout tool: full-system emulation of real boards (multi-node
  networks, sensors, and interconnects included), scriptable, deterministic, runs your
  actual binary in CI. This is how you get "test the firmware on 20 virtual devices with a
  simulated flaky radio" into a pipeline.
- **QEMU** — good for Cortex-A/Linux and some M-profile boards; less peripheral fidelity
  than Renode for MCU work.
- **Wokwi** — browser-based, excellent for ESP32/Arduino/RP2040 prototyping and teaching;
  has a CI mode.
- **HIL (hardware-in-the-loop)** — real MCU running real firmware, with the plant
  simulated in real time (Speedgoat, dSPACE, or a home-built RT Linux box with an FPGA
  I/O card). Essential for motor/vehicle/process control where you cannot test failure
  modes on the real plant. The realistic minimum viable HIL is a second MCU or a Raspberry
  Pi plus a logic-level interface, driving the DUT's inputs and asserting on its outputs.
- **Hardware test farm**: a rack of real boards with programmable power supplies (to test
  brown-out and power-fail-during-write), relay-switched network, and a CI runner. The
  single most valuable piece of infrastructure a firmware team can build after host tests.

### 12.4 Static analysis and formal methods

| Tool | Type | Notes |
|---|---|---|
| Compiler warnings | free | `-Wall -Wextra -Wconversion -Wshadow -Wundef -Werror`. **`-Wconversion` alone catches an enormous amount of integer-promotion breakage.** |
| **clang-tidy** | free | Modernization + bug-prone patterns; integrates with CI |
| **Cppcheck** | free | Decent, low false-positive rate, MISRA add-on |
| **PC-lint Plus / Coverity / Klocwork / Parasoft / LDRA / Axivion** | commercial | MISRA/CERT/AUTOSAR rule sets with certification evidence |
| **Polyspace** | commercial | **Abstract interpretation — proves absence** of certain runtime errors, not just finds them |
| **Frama-C** | free | ACSL contracts, deductive verification of C |
| **CBMC** | free | Bounded model checking; **AWS uses it to prove memory safety of FreeRTOS libraries** |
| **SPARK** | commercial | Provable absence of runtime errors in Ada |
| **TLA+ / Alloy** | free | Model the *protocol*, not the code — finds distributed-state bugs before implementation |

**Coverage**: statement → branch → **MC/DC** (modified condition/decision coverage,
required for DO-178C DAL A/B). On-target coverage needs instrumentation (gcov with a
retrieval channel) or trace hardware (ETM). Host-based coverage is far easier and catches
most logic gaps.

### 12.5 Debugging toolkit

| Tool | Reveals | When |
|---|---|---|
| **SWD/JTAG + GDB** (OpenOCD, pyOCD, **probe-rs**, J-Link) | State, breakpoints, memory | Always |
| **SEGGER RTT** | printf-speed logging with ~µs overhead, no UART pin | Always — vastly better than UART printf |
| **defmt** (Rust) | Interned format strings; tiny wire format | Rust projects |
| **ITM / SWO** | Instrumentation trace, printf, timestamps | Cortex-M3+ |
| **ETM / ETB** | Full instruction trace — reconstruct exactly what executed | Hard bugs, timing analysis; needs trace probe |
| **SystemView / Tracealyzer / Percepio** | RTOS task/ISR timeline, blocking, priority inversion | Any RTOS timing problem — this is the tool |
| **Logic analyzer** (Saleae, sigrok) | Protocol decode, timing | Every bus bring-up |
| **Oscilloscope** | Analog reality: ringing, droop, rise time, glitches | Signal integrity, power |
| **GPIO toggle + scope** | ISR latency, task jitter, WCET | The universal timing measurement |
| **Current probe / Otii / Joulescope** | Real energy per operation | Every battery product |
| **ftrace / perf / LTTng / eBPF** | Linux kernel and userspace latency | Embedded Linux |

**The GPIO-toggle technique** deserves emphasis: set a pin high on ISR entry, low on exit;
scope it. You get latency, duration, jitter, and frequency in one shot, with ~2 cycles of
overhead and no tooling. It is the fastest path from "it feels slow" to a number.

**⚠️ GOTCHA — printf debugging changes timing.** A blocking UART `printf` at 115200 baud
takes ~87 µs *per character*. Putting one in an ISR will change the behaviour you're
trying to observe (and often "fix" the bug). Use RTT, defmt, a ring buffer flushed by a
low-priority task, or GPIO toggles.

### 12.6 CI/CD for firmware

A pipeline that actually works:
```
commit
 ├─ format check (clang-format) + lint (clang-tidy, cppcheck/MISRA)
 ├─ host unit tests (Unity/CppUTest) + ASan/UBSan  ....... < 30 s
 ├─ build all targets in a pinned container ............. reproducible
 ├─ size regression gate (flash/RAM vs baseline, fail on >2% growth)
 ├─ simulation tests (Renode) ........................... minutes
 ├─ SBOM generation (SPDX/CycloneDX) + CVE scan ......... CRA evidence
 ├─ artifact signing (HSM-backed) ....................... never a laptop key
 └─ nightly: hardware test farm + power-fail-during-OTA + soak
```
**Version everything into the binary**: git hash, build date, toolchain version, and a
build-type flag, exposed via a diagnostic command. "Which firmware is this device
running?" must have a definitive answer from the device itself.

---
