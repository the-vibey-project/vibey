---
id: skill-28-misconceptions-e9944ffe13
purpose: 28 misconceptions
source: src/vibey_tools/skills/plugins/radio-technology-for-software-devs/skills/radio-reference/SKILL.md
requires: ["skill-27-anti-patterns-5c699a83fa"]
links: ["skill-29-numbers-60a7429ef0"]
---

## §28. Misconceptions

| Misconception | Correction |
|---|---|
| More TX power fixes range | ⚠️ **4× power for 2× range; antenna/placement usually beat it** (§3 → `radio-intuitions-spectrum-link-budget-and-tradeoffs`) |
| Antenna gain amplifies | ⚠️ **It focuses. Gain in one direction is loss in another** (§5 → `radio-antennas-propagation-noise-and-modulation`) |
| Line of sight is enough | ⚠️ **You need ~60% of the Fresnel zone clear** (§6 → `radio-antennas-propagation-noise-and-modulation`) |
| RSSI tells you link quality | ⚠️ **It includes interference. Use SNR** (§7 → `radio-antennas-propagation-noise-and-modulation`) |
| dBm and dB are interchangeable | ⚠️ **dBm is absolute power; dB is a ratio** (§3 → `radio-intuitions-spectrum-link-budget-and-tradeoffs`) |
| Wider channel is always faster | ⚠️ **Wider = more noise and more overlap** (§7 → `radio-antennas-propagation-noise-and-modulation`, §18 → `radio-protocol-stacks-wifi-ble-lpwan-and-gnss`) |
| Advertised PHY rate ≈ throughput | ⚠️ **Roughly half or less, and shared** (§8 → `radio-antennas-propagation-noise-and-modulation`, §18 → `radio-protocol-stacks-wifi-ble-lpwan-and-gnss`) |
| CSMA/CD works on radio | ⚠️ **You can't hear a collision while transmitting** (§13 → `radio-spread-spectrum-ofdm-access-and-sdr`) |
| Carrier sense prevents collisions | ⚠️ **Hidden node problem** (§13 → `radio-spread-spectrum-ofdm-access-and-sdr`) |
| Bluetooth and BLE are the same protocol | ⚠️ **Different protocols, shared brand** (§19 → `radio-protocol-stacks-wifi-ble-lpwan-and-gnss`) |
| Matter is a radio protocol | ⚠️ **It's an application layer over Thread/Wi-Fi/Ethernet** (§21 → `radio-protocol-stacks-wifi-ble-lpwan-and-gnss`) |
| Mesh gives everyone long battery life | ⚠️ **Routers can't sleep. Only leaf nodes do** (§21 → `radio-protocol-stacks-wifi-ble-lpwan-and-gnss`) |
| Nyquist means 2× the highest frequency | ⚠️ **2× the BANDWIDTH; and 1× for complex IQ** (§15 → `radio-spread-spectrum-ofdm-access-and-sdr`) |
| The DC spike is a signal | ⚠️ **LO leakage artefact of direct conversion** (§14 → `radio-spread-spectrum-ofdm-access-and-sdr`) |
| GNSS works indoors | ⚠️ **Signal is below the noise floor; it needs sky view** (§22 → `radio-protocol-stacks-wifi-ble-lpwan-and-gnss`) |
| Encryption alone secures a radio link | ⚠️ **Without replay protection it doesn't** (§25 → `radio-regulatory-security-and-debugging`) |
| ISM bands are unregulated | ⚠️ **Unlicensed ≠ unregulated. Power and duty cycle bind** (§23 → `radio-regulatory-security-and-debugging`) |
| One design ships globally | ⚠️ **Sub-GHz and 6 GHz allocations differ by region** (§23 → `radio-regulatory-security-and-debugging`, §24.1 → `radio-regulatory-security-and-debugging`) |
| 5G RedCap is the IoT default now | ⚠️ **Few markets; LTE Cat-1/Cat-1 bis is the 2026 default** (§24.2 → `radio-regulatory-security-and-debugging`) |
| Wi-Fi 7 certified means full MLO | ⚠️ **Implementations vary; check the mode** (§24.1 → `radio-regulatory-security-and-debugging`) |
| Satellite IoT is a separate protocol | ⚠️ **NTN is NB-IoT/LTE-M over satellite** (§24.2 → `radio-regulatory-security-and-debugging`) |

---
