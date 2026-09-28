---
id: skill-4-the-range-rate-power-triangle-171fbe90d9
purpose: 4 the range rate power triangle
source: src/vibey_tools/skills/plugins/radio-technology-for-software-devs/skills/radio-intuitions-spectrum-link-budget-and-tradeoffs/SKILL.md
requires: ["skill-3-the-link-budget-0834845d0c"]
links: []
---

## §4. The Range / Rate / Power Triangle

**⚠️ Pick two. This is the constraint that determines your protocol choice.**
```
⚠️ LONG RANGE + LOW POWER  → very low data rate    (LoRa, NB-IoT, Sigfox)
⚠️ HIGH RATE + LOW POWER   → short range           (BLE, Zigbee)
⚠️ HIGH RATE + LONG RANGE  → high power            (Wi-Fi, cellular)
```
**⚠️ Why, physically**: **for a fixed receiver, detecting a signal requires a minimum
energy PER BIT above the noise.** ⚠️ **Slowing the data rate means spending more time —
and therefore more energy — per bit, which raises effective sensitivity.** **LoRa's
−137 dBm sensitivity is bought entirely with time** (§10 → `radio-spread-spectrum-ofdm-access-and-sdr`).
**⚠️ And duty cycle is the real power lever, not TX power.** **A device transmitting for
20 ms once an hour at 14 dBm draws almost nothing on average.** ⚠️ **Battery life in LPWAN
designs is dominated by sleep current and message frequency, not by transmit power** —
**which is why a firmware bug that keeps the radio awake destroys a ten-year battery
budget in weeks.**
