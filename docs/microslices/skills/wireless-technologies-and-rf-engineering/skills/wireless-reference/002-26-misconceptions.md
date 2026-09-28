---
id: skill-26-misconceptions-600f2d2076
purpose: 26 misconceptions
source: src/vibey_tools/skills/plugins/wireless-technologies-and-rf-engineering/skills/wireless-reference/SKILL.md
requires: ["skill-25-what-s-live-checked-august-2026-feff1b3f24"]
links: ["skill-27-numbers-ed94d2cd18"]
---

## §26. Misconceptions

| Misconception | Correction |
|---|---|
| Advertised data rate is what you get | ⚠️ **Peak, shared, half-duplex, pre-overhead** (§1 → `wireless-propagation-link-budget-modulation-antennas-and-spectrum`) |
| More transmit power fixes range | ⚠️ **Regulated, and often makes the return path worse** (§5 → `wireless-propagation-link-budget-modulation-antennas-and-spectrum`, §7 → `wireless-wifi-bluetooth-ble-nfc-and-rfid`) |
| 5 GHz is better than 2.4 GHz | ⚠️ **More capacity, less range. Physics, not quality** (§2 → `wireless-propagation-link-budget-modulation-antennas-and-spectrum`) |
| Wider channels are always faster | ⚠️ **Higher noise floor, fewer channels. Often worse when dense** (§6 → `wireless-wifi-bluetooth-ble-nfc-and-rfid`) |
| Antenna gain amplifies | ⚠️ **It's directionality. Passive** (§4 → `wireless-propagation-link-budget-modulation-antennas-and-spectrum`) |
| Higher-gain omni is always better | ⚠️ **It squashes the pattern vertically** (§4 → `wireless-propagation-link-budget-modulation-antennas-and-spectrum`) |
| The antenna is a component you bolt on | ⚠️ **The ground plane and enclosure are part of it** (§4 → `wireless-propagation-link-budget-modulation-antennas-and-spectrum`, §17 → `wireless-antenna-integration-certification-low-power-and-debugging`) |
| Test the radio on a bare board | ⚠️ **The enclosure detunes it. Tune as-built** (§17 → `wireless-antenna-integration-certification-low-power-and-debugging`) |
| MIMO works best with clear line of sight | ⚠️ **Spatial multiplexing needs rich multipath** (§3 → `wireless-propagation-link-budget-modulation-antennas-and-spectrum`) |
| BLE is a newer Bluetooth version | ⚠️ **Different radio and stack, since 4.0 in 2010** (§8 → `wireless-wifi-bluetooth-ble-nfc-and-rfid`) |
| LE Audio means Bluetooth 5.2+ | ⚠️ **Features decoupled from version numbers** (§8 → `wireless-wifi-bluetooth-ble-nfc-and-rfid`) |
| Auracast works on any modern device | ⚠️ **Needs PAwR — 5.4 and later** (§8 → `wireless-wifi-bluetooth-ble-nfc-and-rfid`) |
| Poll a BLE characteristic for updates | ⚠️ **Subscribe. Notifications exist for this** (§9 → `wireless-wifi-bluetooth-ble-nfc-and-rfid`) |
| NFC is short-range because of low power | ⚠️ **Near-field inductive coupling. Physics** (§10 → `wireless-wifi-bluetooth-ble-nfc-and-rfid`) |
| Matter is a wireless protocol | ⚠️ **Application layer over Thread/Wi-Fi/Ethernet** (§11 → `wireless-thread-matter-lora-cellular-uwb-and-choosing`) |
| A mesh of battery sensors self-heals | ⚠️ **Battery devices usually don't route** (§11 → `wireless-thread-matter-lora-cellular-uwb-and-choosing`) |
| RSSI gives you distance | ⚠️ **Terrible proxy. Multipath and obstruction dominate** (§24 → `wireless-security-coexistence-and-positioning`) |
| Signal strength proves proximity | ⚠️ **Relay attacks defeat it. Needs distance bounding** (§22 → `wireless-security-coexistence-and-positioning`, §25.2) |
| Optimize transmit efficiency for battery life | ⚠️ **Sleep current usually dominates** (§19 → `wireless-antenna-integration-certification-low-power-and-debugging`) |
| A coin cell with enough capacity will work | ⚠️ **Peak current capability is separate** (§19 → `wireless-antenna-integration-certification-low-power-and-debugging`) |
| Certification is a final step | ⚠️ **Design for it, pre-test early** (§18 → `wireless-antenna-integration-certification-low-power-and-debugging`) |
| A module means no RF work | ⚠️ **Only if you follow the reference layout exactly** (§16 → `wireless-thread-matter-lora-cellular-uwb-and-choosing`, §17 → `wireless-antenna-integration-certification-low-power-and-debugging`) |
| My wireless mouse is faulty | ⚠️ **Often USB 3 noise desensitizing 2.4 GHz** (§23 → `wireless-security-coexistence-and-positioning`) |
| Interference comes from other people | ⚠️ **In-device coexistence is often the harder problem** (§23 → `wireless-security-coexistence-and-positioning`) |
| Wi-Fi 8 will be much faster | ⚠️ **Peak is broadly flat. It targets edge and percentile** (§25.1) |
| Wi-Fi 8 products mean the standard is done | ⚠️ **Draft hardware. IEEE approval targeted 2028** (§25.1) |
| Ranging requires UWB | ⚠️ **Channel Sounding does it on the BLE radio** (§25.2) |

---
