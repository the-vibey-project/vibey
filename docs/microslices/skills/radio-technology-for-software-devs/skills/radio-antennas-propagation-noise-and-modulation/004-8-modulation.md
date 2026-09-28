---
id: skill-8-modulation-efb6fe582d
purpose: 8 modulation
source: src/vibey_tools/skills/plugins/radio-technology-for-software-devs/skills/radio-antennas-propagation-noise-and-modulation/SKILL.md
requires: ["skill-7-noise-and-interference-fde3733375"]
links: ["skill-9-shannon-s-limit-1554ca7251"]
---

## §8. Modulation

```
ANALOG      AM (amplitude) · FM (frequency) · PM (phase)
DIGITAL
  ASK/OOK   ⚠️ on-off keying. Trivially simple, poor noise performance.
            Very common in cheap 433 MHz remotes
  FSK/GFSK  ⚠️ frequency shifts. Robust, constant envelope (efficient
            amplifiers). BLE, many sub-GHz radios
  PSK       BPSK, QPSK — phase shifts. Better spectral efficiency
  ⚠️ QAM    amplitude AND phase. 16/64/256/1024/4096-QAM.
            ⚠️ Each step up packs more bits per symbol and needs MORE SNR
```
**⚠️ The constellation diagram is the mental model**: **each symbol is a point in
IQ space** (§14 → `radio-spread-spectrum-ofdm-access-and-sdr`); ⚠️ **noise scatters the received points into clouds, and higher-order
QAM packs the points closer together, so the clouds overlap at lower noise.** **This is
exactly why high data rates need short range: 4096-QAM needs a very clean signal.**
**⚠️ Adaptive modulation and coding (AMC) is why real links have variable rates** —
**the radio drops to a more robust scheme as SNR falls.** ⚠️ **Your "150 Mbps" Wi-Fi link
is a peak PHY rate under ideal conditions and shared with everything else in the band.**

---
