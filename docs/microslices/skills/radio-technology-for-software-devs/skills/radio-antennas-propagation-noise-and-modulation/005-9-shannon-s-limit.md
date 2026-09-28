---
id: skill-9-shannon-s-limit-1554ca7251
purpose: 9 shannon s limit
source: src/vibey_tools/skills/plugins/radio-technology-for-software-devs/skills/radio-antennas-propagation-noise-and-modulation/SKILL.md
requires: ["skill-8-modulation-efb6fe582d"]
links: []
---

## §9. Shannon's Limit

```
⚠️ C = B · log₂(1 + SNR)

C = capacity (bits/s) · B = bandwidth (Hz) · SNR = linear (not dB)
```
**⚠️ This is a hard physical bound, not an engineering target.** **No modulation, coding
or clever protocol beats it.**
**⚠️ What it tells you practically:**
- **⚠️ Bandwidth is worth more than power.** **Capacity is LINEAR in bandwidth and only
  LOGARITHMIC in SNR.** **Doubling bandwidth doubles capacity; doubling SNR adds a
  fraction of a bit per symbol.** ⚠️ **This is why every generation of everything chases
  wider channels — 320 MHz in Wi-Fi 7, mmWave in 5G.**
- **⚠️ At high SNR you're in diminishing returns.** **Going from 30 to 40 dB SNR buys
  little.**
- **⚠️ You can trade SNR for bandwidth**, **which is exactly what spread spectrum does
  (§10 → `radio-spread-spectrum-ofdm-access-and-sdr`) — LoRa transmits BELOW the noise floor by using far more bandwidth than the data
  needs.**
