---
id: skill-29-quick-reference-1d33d4b6a2
purpose: 29 quick reference
source: src/vibey_tools/skills/plugins/wireless-technologies-and-rf-engineering/skills/wireless-reference/SKILL.md
requires: ["skill-28-sources-fa77be9993"]
links: ["skill-30-method-5ffdc9ffa9"]
---

## §29. Quick Reference

### 29.1 Picker
| Question | Where |
|---|---|
| Will this link work? | ⚠️ **Do the link budget first** (§2 → `wireless-propagation-link-budget-modulation-antennas-and-spectrum`) |
| Range is poor — what now? | ⚠️ **Antenna and placement before power** (§1 → `wireless-propagation-link-budget-modulation-antennas-and-spectrum`, §17 → `wireless-antenna-integration-certification-low-power-and-debugging`) |
| Which radio for my product? | ⚠️ **Answer power and "talk to what" first** (§16 → `wireless-thread-matter-lora-cellular-uwb-and-choosing`) |
| Module or chip-down? | ⚠️ **Module, unless high volume** (§16 → `wireless-thread-matter-lora-cellular-uwb-and-choosing`, §18 → `wireless-antenna-integration-certification-low-power-and-debugging`) |
| Why is battery life bad? | ⚠️ **Measure SLEEP current on the real board** (§19 → `wireless-antenna-integration-certification-low-power-and-debugging`) |
| BLE throughput too low | ⚠️ **Connection interval, MTU, PHY — not the "2 Mbps"** (§9 → `wireless-wifi-bluetooth-ble-nfc-and-rfid`) |
| Wi-Fi slow in a crowded office | ⚠️ **Narrower channels, lower power, more APs** (§7 → `wireless-wifi-bluetooth-ble-nfc-and-rfid`) |
| Client won't roam | ⚠️ **The client decides, not the AP** (§6 → `wireless-wifi-bluetooth-ble-nfc-and-rfid`) |
| Tag won't read on metal | ⚠️ **Needs on-metal design with a spacer** (§10 → `wireless-wifi-bluetooth-ble-nfc-and-rfid`) |
| Is proximity secure enough? | ⚠️ **No. Relay attacks. Need distance bounding** (§22 → `wireless-security-coexistence-and-positioning`, §25.2) |
| Mouse drops out near the PC | ⚠️ **USB 3 noise. Move the dongle** (§23 → `wireless-security-coexistence-and-positioning`) |
| Should I wait for Wi-Fi 8? | ⚠️ **No, unless you're a dense-deployment operator** (§25.1) |
| Do I need UWB for ranging? | ⚠️ **Maybe not now** (§14 → `wireless-thread-matter-lora-cellular-uwb-and-choosing`, §25.2) |

### 29.2 Wireless product checklist
- [ ] ⚠️ **Link budget computed with realistic path loss, not free space** (§2 → `wireless-propagation-link-budget-modulation-antennas-and-spectrum`)
- [ ] ⚠️ **Regions of sale confirmed — band availability and duty cycle** (§5 → `wireless-propagation-link-budget-modulation-antennas-and-spectrum`)
- [ ] Radio chosen against power budget and connectivity requirement (§16 → `wireless-thread-matter-lora-cellular-uwb-and-choosing`)
- [ ] ⚠️ **Module reference layout followed EXACTLY, keepout respected** (§17 → `wireless-antenna-integration-certification-low-power-and-debugging`)
- [ ] ⚠️ **Antenna tuned with the final enclosure, battery and display fitted** (§17 → `wireless-antenna-integration-certification-low-power-and-debugging`)
- [ ] ⚠️ **Tested on-body if worn** (§17 → `wireless-antenna-integration-certification-low-power-and-debugging`)
- [ ] Sleep current measured, not calculated (§19 → `wireless-antenna-integration-certification-low-power-and-debugging`)
- [ ] Peak current capability of the battery verified (§19 → `wireless-antenna-integration-certification-low-power-and-debugging`)
- [ ] ⚠️ **In-device coexistence considered — every radio and switcher** (§23 → `wireless-security-coexistence-and-positioning`)
- [ ] ⚠️ **Pre-compliance scan before booking a chamber** (§18 → `wireless-antenna-integration-certification-low-power-and-debugging`)
- [ ] ⚠️ **Modular certification conditions not invalidated** (§18 → `wireless-antenna-integration-certification-low-power-and-debugging`)
- [ ] Industry certification budgeted (SIG, Wi-Fi Alliance, carrier) (§18 → `wireless-antenna-integration-certification-low-power-and-debugging`)
- [ ] ⚠️ **Pairing method gives MITM protection — not "Just Works"** (§22 → `wireless-security-coexistence-and-positioning`)
- [ ] ⚠️ **Provisioning window closes; device authenticates too** (§20 → `wireless-antenna-integration-certification-low-power-and-debugging`, §22 → `wireless-security-coexistence-and-positioning`)
- [ ] ⚠️ **Signed firmware update path; debug interfaces disabled** (§22 → `wireless-security-coexistence-and-positioning`)
- [ ] ⚠️ **Tested at range, in the real environment, against golden units** (§21 → `wireless-antenna-integration-certification-low-power-and-debugging`)

---
