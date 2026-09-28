---
id: skill-26-misconceptions-065e09cd61
purpose: 26 misconceptions
source: src/vibey_tools/skills/plugins/computer-peripherals-design-and-standards/skills/periph-reference/SKILL.md
requires: ["skill-25-what-s-live-checked-august-2026-95cd586982"]
links: ["skill-27-numbers-b27dd0ed80"]
---

## §26. Misconceptions

| Misconception | Correction |
|---|---|
| USB-C means fast | ⚠️ **It's a connector. Can be USB 2.0 only** (§3 → `periph-stack-usb-thunderbolt-and-wireless`) |
| All USB-C cables are equivalent | ⚠️ **Speed, power and video are separate capabilities** (§3 → `periph-stack-usb-thunderbolt-and-wireless`, §25.1) |
| A better cable speeds up a slow port | ⚠️ **The slowest link governs** (§25.1) |
| USB 3.0, 3.1 Gen 1 and 3.2 Gen 1x1 differ | ⚠️ **Same 5 Gbps, renamed twice** (§2 → `periph-stack-usb-thunderbolt-and-wireless`) |
| Cables are passive wire | ⚠️ **Above 3 A they carry an e-marker chip and negotiate** (§3 → `periph-stack-usb-thunderbolt-and-wireless`) |
| USB-C always carries 20 V | ⚠️ **5 V until negotiated. That's the safety property** (§3 → `periph-stack-usb-thunderbolt-and-wireless`) |
| USB4 and Thunderbolt 4 are the same | ⚠️ **USB4 makes PCIe and dual-display optional** (§4 → `periph-stack-usb-thunderbolt-and-wireless`) |
| 6KRO is a hardware limitation | ⚠️ **It's the HID boot protocol report format** (§8 → `periph-buses-pcie-hid-keyboards-mice-and-displays`, §9 → `periph-buses-pcie-hid-keyboards-mice-and-displays`) |
| "Anti-ghosting" means NKRO | ⚠️ **Usually blocking. True NKRO needs per-switch diodes** (§9 → `periph-buses-pcie-hid-keyboards-mice-and-displays`) |
| Higher DPI is better | ⚠️ **Interpolated past a point. Accuracy is the real spec** (§10 → `periph-buses-pcie-hid-keyboards-mice-and-displays`) |
| 8 kHz polling is a big upgrade | ⚠️ **Saves under 1 ms. The display is the bigger term** (§21 → `periph-designing-firmware-pcb-and-debugging`) |
| Wireless is inherently laggy | ⚠️ **Good implementations are competitive; variance is the issue** (§5 → `periph-stack-usb-thunderbolt-and-wireless`) |
| Dongle problems are the dongle's fault | ⚠️ **USB 3 ports radiate noise into 2.4 GHz** (§5 → `periph-stack-usb-thunderbolt-and-wireless`) |
| DSC is like streaming compression | ⚠️ **Hardware, visually lossless, microsecond latency** (§11 → `periph-buses-pcie-hid-keyboards-mice-and-displays`, §25.2) |
| Quoted response time is real | ⚠️ **Best-case GtG with overdrive artifacts** (§11 → `periph-buses-pcie-hid-keyboards-mice-and-displays`) |
| "10-bit" panel means 10-bit | ⚠️ **Often 8-bit + FRC dithering** (§11 → `periph-buses-pcie-hid-keyboards-mice-and-displays`) |
| A DisplayPort 2.1 badge means 80 Gbps | ⚠️ **It may be UHBR13.5. Check the tier** (§25.2) |
| Higher sample rates sound better | ⚠️ **Bit depth is dynamic range; rate is bandwidth** (§12 → `periph-audio-printers-storage-controllers-and-haptics`) |
| Device-not-recognized means broken hardware | ⚠️ **Usually a descriptor or power problem** (§19 → `periph-designing-firmware-pcb-and-debugging`) |
| A valid descriptor means a working device | ⚠️ **Malformed descriptors fail silently** (§8 → `periph-buses-pcie-hid-keyboards-mice-and-displays`, §19 → `periph-designing-firmware-pcb-and-debugging`) |
| Test on one OS is enough | ⚠️ **Each parses descriptors differently** (§19 → `periph-designing-firmware-pcb-and-debugging`) |
| You need a custom driver | ⚠️ **If HID fits, you get every OS free** (§8 → `periph-buses-pcie-hid-keyboards-mice-and-displays`, §16 → `periph-designing-firmware-pcb-and-debugging`) |
| Any VID/PID will do for a product | ⚠️ **VIDs are issued and cost money. Don't squat** (§16 → `periph-designing-firmware-pcb-and-debugging`) |
| Mouse double-click means replace it | ⚠️ **Switch wear. Repairable** (§10 → `periph-buses-pcie-hid-keyboards-mice-and-displays`) |
| Stick drift is unavoidable | ⚠️ **Potentiometer wear. Hall-effect eliminates it** (§15 → `periph-audio-printers-storage-controllers-and-haptics`) |
| USB is a trusted connection | ⚠️ **No device authentication. A stick can claim to be a keyboard** (§24 → `periph-compliance-accessibility-and-security`) |
| USB4 improved the security model | ⚠️ **Adds capability, not authentication** (§24 → `periph-compliance-accessibility-and-security`) |

---
