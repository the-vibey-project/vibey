---
id: skill-14-contested-questions-present-both-cases-don-t-adjudicate-2e1e69a4c2
purpose: 14 contested questions present both cases don t adjudicate
source: src/vibey_tools/skills/plugins/embedded-iot-controls/skills/embedded-reference/SKILL.md
requires: []
links: ["skill-15-the-canon-who-and-what-to-cite-fbb941ba4e"]
---

## §14. Contested Questions — present both cases, don't adjudicate

These are the arguments where competent, experienced engineers genuinely disagree. When
asked, give the strongest version of each side and the conditions that favour it. Do not
present one as settled.

### 14.1 HAL vs bare registers
Covered in §2.1 → `embedded-silicon-and-firmware-models`. Favouring factors: HAL when time-to-market, peripheral complexity, and
errata coverage dominate; registers when footprint, worst-case timing, and auditability
dominate. Most shipping products use both, at different layers.

### 14.2 C vs C++ vs Rust
Covered in §3.4 → `embedded-languages-realtime-and-patterns`. The honest summary: **the memory-safety argument for Rust is
technically strong and the ecosystem argument for C is practically strong**, and which
wins depends entirely on your silicon, your team, and whether your product's threat model
or certification path makes memory safety a first-order requirement.

### 14.3 RTOS vs superloop
- *For an RTOS*: independent activities with different rates and blocking I/O become
  tractable; you get standard primitives instead of hand-rolled ones; the ecosystem
  (network stacks, MCUboot, shells) assumes one.
- *For a superloop / time-triggered design*: no context-switch overhead, no per-task
  stacks, no priority inversion, no deadlock, no mutex bugs, and **the timing is
  analyzable by inspection**. A large fraction of shipped embedded products are superloops
  and are more reliable for it. Adding an RTOS to a system that didn't need one adds
  a whole class of concurrency bugs in exchange for nothing.
- The dividing line most people converge on: **an RTOS earns its keep when you have
  genuinely blocking operations at different priorities**, not merely "several things to
  do."

### 14.4 Vendor lock-in vs portability
- *For going all-in on a vendor SDK* (ESP-IDF, nRF Connect SDK, STM32Cube): the
  integration is deep and tested, connectivity stacks come pre-certified, support is real,
  and you ship faster.
- *For a portable core*: silicon shortages happen (2020–23 taught everyone this), pricing
  changes, parts go EOL, and a product line that can't second-source a MCU is a business
  risk. Portability lives in the layered architecture (§5.1 → `embedded-languages-realtime-and-patterns`), not in avoiding the SDK.

### 14.5 OPC UA vs MQTT/Sparkplug for IIoT
Covered in §6.4 → `embedded-industrial-control-connectivity-and-cloud`. Note especially the disputed claim about **OPC UA PubSub adoption** —
proponents describe it as the convergence point; practitioners report limited
production-grade broker implementations and continued dominance of client/server mode as
of 2026. Both observations can be true; be precise about which one you're relying on.

### 14.6 Certification burden vs agility
- *For heavy process*: in safety and regulated domains the artefacts **are** the product;
  retrofitting them is more expensive than producing them (§11.3 → `embedded-security-safety-and-testing`).
- *Against*: process without engineering judgment produces compliant, unsafe systems —
  the Therac-25 and 737 MAX lessons are about organizational and requirements failure, not
  missing paperwork. Certification is necessary and nowhere near sufficient.

### 14.7 Test on hardware vs test on host
- *For hardware-only*: "the only test that counts is on the real thing"; host tests can
  pass while the product fails because your fakes lie.
- *For host-first*: a 10-second feedback loop finds 10× more bugs than a 5-minute one, and
  sanitizers find classes of bug that on-target testing cannot. The synthesis is
  **both**: host tests gate every commit; hardware tests run nightly on a farm.

### 14.8 Zephyr vs FreeRTOS
Covered in §2.3 → `embedded-silicon-and-firmware-models`. Add: for CRA-era products the maintained-security-process argument
favours Zephyr or FreeRTOS-LTS-with-EMP over any unmaintained or in-house kernel — the
"we wrote our own scheduler" option now carries a regulatory cost it didn't in 2015.

---
