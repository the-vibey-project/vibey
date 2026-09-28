---
id: skill-16-sdr-toolchain-9ce2b4f6ae
purpose: 16 sdr toolchain
source: src/vibey_tools/skills/plugins/radio-technology-for-software-devs/skills/radio-spread-spectrum-ofdm-access-and-sdr/SKILL.md
requires: ["skill-15-sampling-and-dsp-essentials-c59f03228b"]
links: []
---

## §16. SDR Toolchain

```
⚠️ RTL-SDR       ~$30, RX only, ~24–1766 MHz, 8-bit, ~2.4 MHz BW.
   ⚠️ Start here. A repurposed TV tuner and genuinely capable for learning
HackRF One       ~$300, TX+RX (half duplex), 1 MHz–6 GHz, 8-bit, 20 MHz
LimeSDR / PlutoSDR  mid-range, full duplex, better ADCs
USRP (Ettus)     ⚠️ research/production grade, expensive, excellent
BladeRF          mid-high

SOFTWARE
⚠️ GNU Radio     flowgraph-based DSP framework. The standard. Python/C++ blocks
SoapySDR         ⚠️ hardware abstraction — write once, swap radios
GQRX / SDR++ / SDRangel   general-purpose receivers and spectrum viewing
Inspectrum       ⚠️ excellent for visually reverse-engineering a capture
Universal Radio Hacker  ⚠️ purpose-built for protocol reverse engineering
liquid-dsp / NumPy+SciPy   ⚠️ roll your own; NumPy is fine for offline work
srsRAN / OpenAirInterface  open-source LTE/5G stacks
```
**⚠️ A learning path that actually works**: **receive FM broadcast (proves the chain) →
decode ADS-B aircraft transponders at 1090 MHz (real digital demodulation, instant visible
results) → decode a 433 MHz sensor around your home (OOK, simple, and it teaches framing)
→ then attempt transmit — carefully, and see §23 → `radio-regulatory-security-and-debugging` first.**

---

# PART III — PROTOCOLS
