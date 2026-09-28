---
id: skill-16-designing-a-custom-peripheral-afaea6c199
purpose: 16 designing a custom peripheral
source: src/vibey_tools/skills/plugins/computer-peripherals-design-and-standards/skills/periph-designing-firmware-pcb-and-debugging/SKILL.md
requires: []
links: ["skill-17-firmware-b57ef2da16"]
---

## §16. Designing a Custom Peripheral

```
⚠️ THE DECISION ORDER
   ⚠️ 1. What DEVICE CLASS is it? (§8) ⚠️ If HID fits, you get
      cross-platform support free. ⚠️ Vendor-specific means
      writing and maintaining drivers forever — avoid unless
      genuinely necessary
   ⚠️ 2. Wired or wireless? (§5)
   ⚠️ 3. Power budget and source
   ⚠️ 4. Microcontroller selection — ⚠️ NATIVE USB peripheral vs
      bit-banged vs a USB bridge chip
   ⚠️ 5. Enclosure and manufacturing method
⚠️ COMMON MCU CHOICES  ⚠️ RP2040/RP2350 (cheap, native USB, PIO) ·
   STM32 · ATmega32U4 (the classic HID choice) · nRF52 (BLE) ·
   ESP32 (Wi-Fi/BLE)
⚠️ ⚠️ VID/PID  ⚠️ USB Vendor IDs are ISSUED BY THE USB-IF AND COST
   MONEY. ⚠️ For hobby projects, use a PID sublicensed from a
   chip vendor's range or a community allocation — ⚠️ do NOT
   ship products with a squatted VID, which is common and wrong
⚠️ PROTOTYPE PATH  breadboard → dev board → custom PCB →
   ⚠️ and expect at least two board revisions
```

---
