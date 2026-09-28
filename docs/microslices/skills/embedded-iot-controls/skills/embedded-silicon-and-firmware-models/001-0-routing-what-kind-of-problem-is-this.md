---
id: skill-0-routing-what-kind-of-problem-is-this-70b909b916
purpose: 0 routing what kind of problem is this
source: src/vibey_tools/skills/plugins/embedded-iot-controls/skills/embedded-silicon-and-firmware-models/SKILL.md
requires: []
links: ["skill-1-silicon-memory-and-peripherals-73dbb370c6"]
---

## §0. Routing — What Kind of Problem Is This?

Before answering an embedded question, classify it. The right answer changes completely
across these axes, and most bad advice comes from answering in the wrong frame.

### 0.1 The compute-class decision

| Class | Typical part | RAM | Runs | Boot time | Power floor | Use when |
|---|---|---|---|---|---|---|
| 8/16-bit MCU | AVR, MSP430, PIC | 0.5–16 KB | Superloop | <10 ms | ~100 nA sleep | BOM cost dominates; single function |
| 32-bit MCU (bare/RTOS) | Cortex-M0+/M4/M33, ESP32-C6, RISC-V | 16 KB–1 MB | Superloop or RTOS | <50 ms | ~1 µA stop | Hard real-time, battery, deterministic |
| MCU + connectivity SoC | nRF54, ESP32-S3, STM32WB | 256 KB–2 MB | RTOS (Zephyr/FreeRTOS) | <200 ms | ~2 µA | Wireless product, OTA, cloud |
| MPU / applications SoC | i.MX8, STM32MP2, RK3588, ESP32-P4 | 128 MB–8 GB | Linux | 1–20 s | ~50 mW | Filesystem, networking stack, GUI, ML |
| Hybrid AMP | i.MX8 (A-core Linux + M-core RTOS) | both | both | both | both | Real-time control **and** rich connectivity |
| FPGA / SoC-FPGA | Zynq, PolarFire SoC | — | HDL + optional CPU | — | high | Sub-µs determinism, custom protocol, massive I/O parallelism |
| PLC / soft-PLC | S7-1500, ControlLogix, TwinCAT | — | IEC 61131-3 scan | — | mains | Regulated industrial process, maintainable by plant electricians |

**[UNIVERSAL] The single most consequential architectural question in embedded work is
"MCU or MPU?" — because it decides everything downstream:** language, OS, update
mechanism, security model, certification path, team skill set, and BOM. A wrong answer
here costs a redesign, not a refactor.

**Decision heuristics:**
- Need a filesystem, TCP/IP with TLS 1.3, or >1 MB of code? → MPU/Linux.
- Need guaranteed response inside 100 µs? → MCU or FPGA. Linux (even PREEMPT_RT) is
  soft/firm real-time, not hard.
- Need to run on a coin cell for 5 years? → MCU, and the radio duty cycle dominates the
  budget, not the CPU.
- Need both? → AMP (Linux + M-core), or two chips. Do not try to make Linux hard real-time
  when the requirement is a 10 kHz current loop.

### 0.2 The scheduling-model decision

```
Is there more than one activity with independent timing?
├── No  → superloop. Stop here. Do not add an RTOS.
└── Yes → Are the activities mostly I/O-bound and event-driven?
          ├── Yes → cooperative/event-driven (QP active objects, Embassy async,
          │         time-triggered) — smallest RAM, easiest to reason about
          └── No (CPU-bound with different deadlines)
                    → preemptive RTOS with rate-monotonic priorities
```

**[CONTESTED]** "Always use an RTOS" vs. "superloops are underrated" — see §14.3 → `embedded-reference`.

### 0.3 The question-type router

| If asked about... | Go to |
|---|---|
| Registers, clocks, peripherals, DMA, power | §1 |
| HAL vs registers, RTOS choice, Zephyr/FreeRTOS, Yocto | §2 |
| C vs C++ vs Rust vs MicroPython, MISRA | §3 → `embedded-languages-realtime-and-patterns` |
| Priority inversion, WCET, atomics, memory barriers | §4 → `embedded-languages-realtime-and-patterns` |
| Ring buffers, state machines, error handling, driver structure | §5 → `embedded-languages-realtime-and-patterns` |
| PLC, Modbus, EtherCAT, OPC UA, SCADA, Purdue model | §6 → `embedded-industrial-control-connectivity-and-cloud` |
| PID, anti-windup, motor control, sensor fusion | §7 → `embedded-industrial-control-connectivity-and-cloud` |
| BLE, Thread, Matter, LoRa, cellular, MQTT, CoAP | §8 → `embedded-industrial-control-connectivity-and-cloud` |
| Provisioning, OTA, fleet observability, digital twin | §9 → `embedded-industrial-control-connectivity-and-cloud` |
| Secure boot, TLS on MCU, CRA, RED, IEC 62443 | §10 → `embedded-security-safety-and-testing` |
| SIL/ASIL/DAL, FMEDA, MPU partitioning, lockstep | §11 → `embedded-security-safety-and-testing` |
| Unit testing firmware, HIL, static analysis, debugging | §12 → `embedded-security-safety-and-testing` |
| Board bring-up, hardware/firmware co-development | §13 → `embedded-security-safety-and-testing` |
| "Which is better, X or Y?" | §14 → `embedded-reference` (contested) |
| Books, authorities, canonical references | §15 → `embedded-reference` |
| Famous failures and what they teach | §16 → `embedded-reference` |
| "Is this still current?" | §17 → `embedded-reference` |

---
