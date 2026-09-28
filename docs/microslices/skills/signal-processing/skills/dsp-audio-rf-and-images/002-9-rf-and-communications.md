---
id: skill-9-rf-and-communications-44d4f48b46
purpose: 9 rf and communications
source: src/vibey_tools/skills/plugins/signal-processing/skills/dsp-audio-rf-and-images/SKILL.md
requires: ["skill-8-audio-and-speech-94e0feb365"]
links: ["skill-10-images-and-video-ba9cf5a77e"]
---

## §9. RF and Communications

**Modulation**: analogue (AM/FM/PM), digital (**ASK/FSK/PSK/QAM**), and **OFDM** —
⚠️ **which converts a frequency-selective channel into many flat sub-channels and is why
it's in Wi-Fi, LTE, 5G, and DVB.** **Spread spectrum** (DSSS, FHSS) for interference
resistance and multiple access.

**The receive chain**: down-conversion to **I/Q baseband** (⚠️ **complex-valued
representation is the whole language of RF DSP — get comfortable with it**),
**matched filtering** (§4 → `dsp-convolution-multirate-and-spectral-analysis`), **timing and carrier recovery**, **equalization** (§6 → `dsp-convolution-multirate-and-spectral-analysis`), and
**demodulation**.

**Error correction**: Hamming and Reed–Solomon (⚠️ **still the standard for burst errors in
storage and broadcast**), convolutional codes with Viterbi decoding, **Turbo**, **LDPC**
(⚠️ **near-Shannon-limit, and in 5G, Wi-Fi 6 and DVB-S2**), and **polar codes** in 5G
control channels.

**⚠️ The physical realities that dominate**: multipath and fading, Doppler, the noise
figure of your front end, **and the fact that Shannon capacity is a hard ceiling** —
C = B log₂(1 + SNR). **No modulation scheme beats it.**

**SDR** is where software engineers actually meet this: **GNU Radio** (flowgraph-based),
**RTL-SDR** (⚠️ **~$30 and genuinely capable for receive-only experimentation**),
**HackRF**, **USRP**, **LimeSDR**, and **SoapySDR** as the hardware abstraction.
⚠️ **Transmitting requires a licence in most jurisdictions and most bands — receiving
generally doesn't.**

---
