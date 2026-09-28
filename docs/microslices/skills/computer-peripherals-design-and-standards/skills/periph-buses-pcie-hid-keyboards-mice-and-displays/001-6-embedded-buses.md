---
id: skill-6-embedded-buses-3ba69f5d10
purpose: 6 embedded buses
source: src/vibey_tools/skills/plugins/computer-peripherals-design-and-standards/skills/periph-buses-pcie-hid-keyboards-mice-and-displays/SKILL.md
requires: []
links: ["skill-7-pcie-peripherals-e901df6cf3"]
---

## §6. Embedded Buses

**⚠️ For building peripherals rather than connecting them.**
```
⚠️ I²C  ⚠️ two wires, addressed, multi-drop, open-drain with
   pull-ups. ⚠️ Slow (100k/400k/1M), and ⚠️ ADDRESS COLLISIONS
   between chips are a classic design trap
⚠️ SPI  ⚠️ four wires, fast, full duplex, ⚠️ no addressing — one
   chip-select line PER DEVICE. Displays, sensors, flash
⚠️ UART / serial  ⚠️ no clock, both ends must agree on baud rate.
   ⚠️ Still the universal debug interface
⚠️ 1-Wire, CAN (automotive/industrial), RS-485 (long runs,
   differential, multi-drop)
⚠️ ⚠️ PS/2 IS INTERRUPT-DRIVEN, not polled — ⚠️ which is why it had
   genuinely lower latency than early USB and why it persists in
   niche uses
⚠️ GPIO, ADC, PWM, and interrupt handling are the primitives
   everything else is built from
```

---
