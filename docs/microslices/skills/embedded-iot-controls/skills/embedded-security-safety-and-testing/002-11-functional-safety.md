---
id: skill-11-functional-safety-37c9804c6f
purpose: 11 functional safety
source: src/vibey_tools/skills/plugins/embedded-iot-controls/skills/embedded-security-safety-and-testing/SKILL.md
requires: ["skill-10-security-e8b2a6af03"]
links: ["skill-12-testing-verification-and-debugging-534af92c27"]
---

## §11. Functional Safety

### 11.1 The standards map

| Standard | Domain | Levels | Notes |
|---|---|---|---|
| **IEC 61508** | Generic / industrial (parent standard) | SIL 1–4 | The root from which most others derive |
| **ISO 26262** | Automotive | ASIL A–D (+QM) | Adds ASIL decomposition, HARA, item definition |
| **IEC 62061 / ISO 13849** | Machinery | SIL CL 1–3 / PL a–e | 13849 uses categories + MTTFd + DC + CCF |
| **IEC 61511** | Process industry | SIL 1–3 | Safety Instrumented Systems; sits on 61508 |
| **DO-178C** | Airborne software | DAL A–E | Objectives-based; **MC/DC coverage required at DAL A/B** |
| **IEC 62304** | Medical device software | Class A/B/C | Lifecycle process standard, not a technique standard |
| **EN 50128 / EN 50657** | Rail | SIL 0–4 | Rail-specific software |
| **ISO 25119 / ISO 13849** | Agricultural machinery | AgPL | |

**[UNIVERSAL] These are *process* standards.** They do not tell you how to write good code;
they tell you what evidence you must produce that you wrote it deliberately, verified it,
and can trace every requirement to a test. The artefacts are the deliverable.

### 11.2 The quantitative core

- **PFD_avg** (probability of failure on demand) for low-demand systems; **PFH**
  (probability of dangerous failure per hour) for high-demand/continuous. SIL bands are
  defined by these numbers — e.g. SIL 2 continuous mode is PFH between 10⁻⁷ and 10⁻⁶ /h.
- **SFF** (safe failure fraction) and **HFT** (hardware fault tolerance) jointly cap the
  achievable SIL for a given architecture.
- **Diagnostic Coverage (DC)** — the fraction of dangerous failures detected by
  diagnostics. This is where firmware earns its keep: RAM march tests, CPU register tests,
  flash CRC, program-flow monitoring, watchdog with window, and plausibility checks all
  raise DC.
- **Architectures**: 1oo1 (no redundancy), **1oo1D** (with diagnostics), 1oo2 (either
  channel can trip — safe but nuisance-trip-prone), 2oo2 (both must agree — available but
  less safe), **2oo3** (voting — the classic high-availability-and-safety compromise).
- **Analysis methods**: **FMEA/FMEDA** (bottom-up, component→effect, produces the failure
  rates that feed PFD), **FTA** (top-down from the hazard), **HAZOP** (guideword-driven
  process hazard study), **LOPA** (layer of protection analysis → determines required SIL).

### 11.3 Firmware techniques that produce safety evidence

- **Memory partitioning with the MPU**: each task gets only the regions it needs.
  This provides **freedom from interference** — the property that lets you run a
  lower-integrity task (comms, UI) alongside a safety task on one MCU without inheriting
  its integrity requirement. Without it, *everything* on the chip must be developed to the
  highest ASIL/SIL present, which is ruinously expensive. This is why FreeRTOS's expanded
  MPU support and Zephyr's user-mode/memory-domain features matter commercially.
- **Lockstep cores** (Cortex-R5F in lockstep, TI Hercules, Infineon AURIX): two cores
  execute identically with a cycle offset; a comparator flags divergence. Gives very high
  DC for the CPU itself.
- **ECC on RAM and flash**; **CRC over the whole program image checked at boot** and
  periodically in the background.
- **Program flow monitoring**: a checksum accumulated across control-flow checkpoints,
  verified against the expected value; catches wild jumps and skipped code.
- **Periodic self-tests**: RAM march-C, CPU register/ALU tests, ADC reference plausibility,
  clock cross-check (verify the main oscillator against an independent low-speed one).
- **Defined safe state** and a bounded **fault reaction time interval**: the total time
  from fault occurrence to reaching the safe state must be less than the process safety
  time. Every diagnostic's detection latency counts against this budget.
- **Tool qualification**: your compiler, static analyzer, and code generator need
  qualification evidence proportionate to their ability to inject or fail to detect an
  error (ISO 26262 TCL, DO-178C tool qualification levels). This is why qualified
  toolchains (compiler vendors' safety packs, **Ferrocene** for Rust) command a premium.

> **⚠️ GOTCHA — "we'll certify it later."** Retrofitting certification onto existing code
> is typically more expensive than rewriting it. Requirements traceability, a documented
> development process, and coverage evidence must exist *from the start*. Deciding at
> month 18 that the product needs SIL 2 is a schedule catastrophe, not a paperwork
> exercise.

---
