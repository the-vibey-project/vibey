---
id: skill-7-noise-and-interference-fde3733375
purpose: 7 noise and interference
source: src/vibey_tools/skills/plugins/radio-technology-for-software-devs/skills/radio-antennas-propagation-noise-and-modulation/SKILL.md
requires: ["skill-6-propagation-and-fading-5018edd42f"]
links: ["skill-8-modulation-efb6fe582d"]
---

## §7. Noise and Interference

```
⚠️ THERMAL NOISE FLOOR = −174 dBm/Hz at room temperature
   ⚠️ In 1 MHz of bandwidth: −174 + 10·log₁₀(10⁶) = −114 dBm
   ⚠️ WIDER BANDWIDTH = MORE NOISE. This is why narrowband radios are
   more sensitive than wideband ones
NOISE FIGURE (NF)  how much your receiver adds. 2–10 dB typical
SNR                signal-to-noise. ⚠️ What actually determines whether you
                   can demodulate
SINR               ⚠️ includes interference — the realistic metric
```
**⚠️ Interference sources that actually bite in the field**: **microwave ovens (2.4 GHz,
and they pulse at the mains frequency); other Wi-Fi and BLE; USB 3.0 and its cables,
which radiate broadband noise right at 2.4 GHz; switching power supplies; LED drivers;
poorly shielded cheap electronics; and your own device's digital sections.**
> **⚠️ GOTCHA — self-interference is the one people miss.** ⚠️ **A switching regulator,
> a high-speed digital bus, or a display ribbon cable on the same board can raise your
> receiver's effective noise floor by tens of dB.** **Symptom: sensitivity is far worse
> than the datasheet and only in the finished product.** **Diagnosis: turn subsystems off
> one at a time and watch the noise floor.**

**⚠️ RSSI is not SNR, and confusing them causes bad decisions.** **RSSI measures total
received power INCLUDING interference.** ⚠️ **A strong RSSI in a noisy band can mean a
worse link than a weak RSSI in a quiet one.** **Use SNR/LQI where the radio provides it.**

---
