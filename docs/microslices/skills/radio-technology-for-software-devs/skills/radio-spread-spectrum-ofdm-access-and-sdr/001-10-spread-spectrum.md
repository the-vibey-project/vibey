---
id: skill-10-spread-spectrum-bdef21050d
purpose: 10 spread spectrum
source: src/vibey_tools/skills/plugins/radio-technology-for-software-devs/skills/radio-spread-spectrum-ofdm-access-and-sdr/SKILL.md
requires: []
links: ["skill-11-ofdm-fbc6424340"]
---

## §10. Spread Spectrum

**⚠️ Deliberately using much more bandwidth than the data requires, in exchange for
robustness.**
```
DSSS   ⚠️ multiply data by a fast pseudo-random code. Spreads energy;
       the receiver correlates to recover it, gaining PROCESSING GAIN.
       Interference and multipath are suppressed. 802.15.4, GPS, older Wi-Fi
FHSS   ⚠️ hop the carrier around a channel set. If one channel is jammed
       you lose one hop, not the link. ⚠️ Bluetooth — 1600 hops/second
CSS    ⚠️ chirp spread spectrum — LoRa. Frequency sweeps across the band
CDMA   multiple users, different codes, same band and time
```
**⚠️ LoRa's spreading factor is the clearest illustration of §4 → `radio-intuitions-spectrum-link-budget-and-tradeoffs` in a single knob:**
⚠️ **SF7 → SF12 roughly doubles airtime per step, adds a few dB of sensitivity per step,
and cuts the data rate.** **SF12 reaches furthest and can occupy the channel for seconds
per message** — ⚠️ **which collides directly with duty-cycle regulation (§23 → `radio-regulatory-security-and-debugging`) and destroys
network capacity if used carelessly.** **Adaptive Data Rate exists to push devices to the
lowest SF that works.**

---
