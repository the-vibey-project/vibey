---
id: skill-17-firmware-b57ef2da16
purpose: 17 firmware
source: src/vibey_tools/skills/plugins/computer-peripherals-design-and-standards/skills/periph-designing-firmware-pcb-and-debugging/SKILL.md
requires: ["skill-16-designing-a-custom-peripheral-afaea6c199"]
links: ["skill-18-pcb-and-mechanical-design-60162855c8"]
---

## §17. Firmware

**⚠️ The mature open ecosystems save enormous effort**: ⚠️ **QMK and ZMK for keyboards
(⚠️ ZMK being BLE-first), CircuitPython and Arduino for rapid work, TinyUSB as the
portable USB stack, and vendor HALs underneath.**
**⚠️ What the firmware actually does**: ⚠️ **matrix scanning and debounce (§9 → `periph-buses-pcie-hid-keyboards-mice-and-displays`), layer and
macro handling, descriptor generation, endpoint management, and persistent configuration.**
**⚠️ The real-time discipline**: ⚠️ **interrupt latency, avoiding blocking in the main loop,
and keeping the USB polling deadline no matter what else is happening.**
**⚠️ Power management for battery devices** is usually where naive firmware fails —
⚠️ **sleep states, wake sources, and connection interval negotiation dominate battery life
far more than the radio's rated current.**
**⚠️ DFU and bootloaders** — ⚠️ **and always leave a hardware recovery path, because
bricking a device with no bootloader entry is the classic first-project disaster.**

---
