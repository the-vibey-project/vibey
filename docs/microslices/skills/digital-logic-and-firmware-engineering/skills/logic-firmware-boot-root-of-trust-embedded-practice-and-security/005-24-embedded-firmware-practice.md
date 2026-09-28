---
id: skill-24-embedded-firmware-practice-8933cbe46f
purpose: 24 embedded firmware practice
source: src/vibey_tools/skills/plugins/digital-logic-and-firmware-engineering/skills/logic-firmware-boot-root-of-trust-embedded-practice-and-security/SKILL.md
requires: ["skill-23-acpi-and-platform-interfaces-9c9d2cc3c8"]
links: ["skill-25-firmware-security-de5b152236"]
---

## §24. Embedded Firmware Practice

**⚠️ The startup sequence before `main()`**: ⚠️ **vector table, stack pointer, copying
initialized data from flash to RAM, zeroing BSS, calling constructors — ⚠️ and knowing this
is what lets you debug a device that never reaches `main`.**
**⚠️ The linker script and memory map** are first-class design artifacts, not boilerplate.
**⚠️ Interrupts**: ⚠️ **keep ISRs short, understand priority and nesting, ⚠️ and volatile
plus atomic access for anything shared with an ISR — ⚠️ noting that `volatile` is NOT a
synchronization primitive** (see a microarchitecture reference §8).
**⚠️ Bare metal versus RTOS**: ⚠️ **superloop with a state machine is often the right answer;
an RTOS buys preemption and structure at the cost of stack-per-task and a scheduler to
reason about.**
**⚠️ Watchdogs** — ⚠️ **and the discipline that a watchdog must be fed from a place that
proves the system is actually working, not from a timer interrupt that runs regardless.**
**⚠️ Field update is the hardest requirement**: ⚠️ **A/B partitions, atomic switchover,
power-fail safety, rollback, and a recovery path that cannot itself be bricked** (see a
peripherals reference §17).

---
