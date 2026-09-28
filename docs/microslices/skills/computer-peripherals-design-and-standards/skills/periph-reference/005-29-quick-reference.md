---
id: skill-29-quick-reference-1fc0adf64b
purpose: 29 quick reference
source: src/vibey_tools/skills/plugins/computer-peripherals-design-and-standards/skills/periph-reference/SKILL.md
requires: ["skill-28-sources-2f308513ef"]
links: ["skill-30-method-921b1b66a7"]
---

## §29. Quick Reference

### 29.1 Picker
| Question | Where |
|---|---|
| Will this cable do what I need? | ⚠️ **Check speed, power AND video separately** (§3 → `periph-stack-usb-thunderbolt-and-wireless`, §25.1) |
| Why won't my device enumerate? | ⚠️ **Read the descriptors first** (§19 → `periph-designing-firmware-pcb-and-debugging`) |
| Why does my keyboard fail in BIOS? | ⚠️ **NKRO vs boot protocol** (§8 → `periph-buses-pcie-hid-keyboards-mice-and-displays`, §9 → `periph-buses-pcie-hid-keyboards-mice-and-displays`) |
| Do I need a driver? | ⚠️ **If HID fits, no** (§8 → `periph-buses-pcie-hid-keyboards-mice-and-displays`, §16 → `periph-designing-firmware-pcb-and-debugging`) |
| Why is my input laggy? | ⚠️ **Measure the whole chain; suspect the display** (§21 → `periph-designing-firmware-pcb-and-debugging`) |
| Is 8 kHz polling worth it? | ⚠️ **Under 1 ms. Almost never the limit** (§21 → `periph-designing-firmware-pcb-and-debugging`) |
| Wireless or wired? | ⚠️ **Latency is close now; power and congestion decide** (§5 → `periph-stack-usb-thunderbolt-and-wireless`) |
| Do I need UHBR20? | ⚠️ **Only for confirmed uncompressed 4K 240 Hz+** (§25.2) |
| Is DSC bad? | ⚠️ **No. Visually lossless, microseconds** (§11 → `periph-buses-pcie-hid-keyboards-mice-and-displays`, §25.2) |
| Why did my drive slow down? | ⚠️ **Hub shares upstream bandwidth** (§14 → `periph-audio-printers-storage-controllers-and-haptics`) |
| Is this USB stick safe to plug in? | ⚠️ **It can claim to be a keyboard. Don't** (§24 → `periph-compliance-accessibility-and-security`) |
| What MCU for a custom HID device? | ⚠️ **Native USB peripheral; RP2040/STM32/nRF52** (§16 → `periph-designing-firmware-pcb-and-debugging`) |

### 29.2 Custom peripheral checklist
- [ ] ⚠️ **Device class chosen — HID if at all possible** (§8 → `periph-buses-pcie-hid-keyboards-mice-and-displays`, §16 → `periph-designing-firmware-pcb-and-debugging`)
- [ ] ⚠️ **Report descriptor validated, not just compiled** (§8 → `periph-buses-pcie-hid-keyboards-mice-and-displays`, §19 → `periph-designing-firmware-pcb-and-debugging`)
- [ ] ⚠️ **Correct usage page and usages for the device KIND** (§8 → `periph-buses-pcie-hid-keyboards-mice-and-displays`)
- [ ] Endpoint type matches the traffic pattern (§2 → `periph-stack-usb-thunderbolt-and-wireless`)
- [ ] ⚠️ **Current draw declared honestly and inrush handled** (§19 → `periph-designing-firmware-pcb-and-debugging`)
- [ ] ⚠️ **90 Ω differential pairs, matched, continuous ground plane** (§18 → `periph-designing-firmware-pcb-and-debugging`)
- [ ] ⚠️ **ESD protection on every exposed line** (§18 → `periph-designing-firmware-pcb-and-debugging`)
- [ ] Connector mechanically retained (§18 → `periph-designing-firmware-pcb-and-debugging`)
- [ ] ⚠️ **Legitimate VID/PID — not squatted** (§16 → `periph-designing-firmware-pcb-and-debugging`)
- [ ] ⚠️ **Bootloader with a hardware recovery path** (§17 → `periph-designing-firmware-pcb-and-debugging`)
- [ ] ⚠️ **Tested on Windows, macOS, Linux AND in BIOS** (§19 → `periph-designing-firmware-pcb-and-debugging`)
- [ ] ⚠️ **Onboard profile storage so it works without vendor software** (§20 → `periph-designing-firmware-pcb-and-debugging`)
- [ ] Remappable, and doesn't rely on colour alone (§23 → `periph-compliance-accessibility-and-security`)
- [ ] ⚠️ **Pre-compliance EMC scan before booking a chamber** (§22 → `periph-compliance-accessibility-and-security`)

---
