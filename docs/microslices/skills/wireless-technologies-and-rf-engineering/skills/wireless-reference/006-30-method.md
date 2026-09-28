---
id: skill-30-method-5ffdc9ffa9
purpose: 30 method
source: src/vibey_tools/skills/plugins/wireless-technologies-and-rf-engineering/skills/wireless-reference/SKILL.md
requires: ["skill-29-quick-reference-1d33d4b6a2"]
links: []
---

## §30. Method

**§1–§24 → `wireless-propagation-link-budget-modulation-antennas-and-spectrum`, `wireless-wifi-bluetooth-ble-nfc-and-rfid`, `wireless-thread-matter-lora-cellular-uwb-and-choosing`, `wireless-antenna-integration-certification-low-power-and-debugging`, `wireless-security-coexistence-and-positioning` rests on settled physics and mature standards** — **the link budget, free-space
path loss, OFDM, CSMA/CA, the GATT model, near-field coupling in NFC, and the
certification regime.** ⚠️ **None needed verification; Friis published the transmission
equation in 1946 and the Chu-Harrington limit on small antennas is not going to move.**

**Two searches were run in August 2026**, on **Wi-Fi 8** and **Bluetooth Channel Sounding**
— ⚠️ **the first because 802.11bn represents a genuine change in what a Wi-Fi generation is
FOR, the second because it puts secure ranging on the radio that is already in everything,
which changes a real design decision.**

**Confidence.** **High** in §2 → `wireless-propagation-link-budget-modulation-antennas-and-spectrum` and §4 → `wireless-propagation-link-budget-modulation-antennas-and-spectrum`, which are the sections I'd most want read.
⚠️ **The link budget predicts more than any amount of protocol knowledge, and the dB
intuition — 3 dB doubles, doubling distance costs 6 dB — is what lets you sanity-check a
claim in your head.** ⚠️ **§4 → `wireless-propagation-link-budget-modulation-antennas-and-spectrum`'s "gain is directionality, not amplification" and "the ground
plane is part of the antenna" are the two corrections that most often prevent a product
from being designed wrong months before anyone measures it.** **§19 → `wireless-antenna-integration-certification-low-power-and-debugging`'s point that sleep
current usually dominates battery life is the one that most often saves a project.**

**High** on §25.1's targets, which come from the IEEE 802.11bn PAR as reported by Samsung
Research: ⚠️ **at least 25% higher throughput in challenging conditions, 25% lower 95th-
percentile latency, 25% fewer dropped packets.** ⚠️ **Those are percentile and edge-case
figures rather than peak-rate ones, and reading them correctly is the whole point of the
section.**
⚠️ **The timeline is the practically important part and it is consistent across sources
including ones with nothing to sell: IEEE approval targeted 2028, draft hardware shown at
CES 2026, and the sensible advice being that Wi-Fi 7 is the standard for this cycle.**
**⚠️ Vendor trial figures (Co-SR at 15–25%) are marked as reported.**

**Moderate-to-high** on §25.2. ⚠️ **The specification facts are solid and come from the
Bluetooth SIG directly: Channel Sounding in Core 6.0 from August 2024, combining
phase-based ranging and round-trip timing, designed for digital keys and Find My
networks.**
⚠️ **The ACCURACY CLAIMS are where I'd hold back — sources give "tens of centimetres",
"±10 cm at 10 m" and "centimetre-level up to 150 metres", which cannot all describe the
same thing, and active research on complex indoor environments suggests the hard cases are
unsolved.** **⚠️ I have reported the range and named sub-metre as the safe claim rather
than repeating the most flattering figure.**
⚠️ **The security framing is the durable content: distance bounding defeats relay attacks
in a way signal strength fundamentally cannot, and that is a §22 → `wireless-security-coexistence-and-positioning` problem that has needed a
real answer for years.**
