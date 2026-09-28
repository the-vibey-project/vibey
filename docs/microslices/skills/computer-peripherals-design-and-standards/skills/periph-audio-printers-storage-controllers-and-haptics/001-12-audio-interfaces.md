---
id: skill-12-audio-interfaces-0a99455689
purpose: 12 audio interfaces
source: src/vibey_tools/skills/plugins/computer-peripherals-design-and-standards/skills/periph-audio-printers-storage-controllers-and-haptics/SKILL.md
requires: []
links: ["skill-13-printers-and-scanners-dc0ca49b59"]
---

## §12. Audio Interfaces

**⚠️ The signal chain**: ⚠️ **transducer → preamp → ADC → digital → DAC → amplifier →
transducer, and the weakest link governs.**
**⚠️ Sample rate and bit depth**: ⚠️ **bit depth sets DYNAMIC RANGE, sample rate sets
BANDWIDTH via Nyquist; ⚠️ and higher-than-necessary rates mainly buy filter headroom, not
audible quality — the honest case for high rates is in production, not playback.**
**⚠️ Latency** is the peripheral-specific problem: ⚠️ **buffer size trades latency against
dropouts, and driver model matters enormously — ASIO, WASAPI exclusive, CoreAudio and
JACK exist because the general OS mixer path is too slow for monitoring.**
**⚠️ USB Audio Class 2** gives driver-free high-rate multichannel audio; ⚠️ **UAC1 is
limited but works on hosts lacking UAC2 support.**
**⚠️ Impedance matching** for headphones, ⚠️ **phantom power for condenser microphones, and
balanced versus unbalanced connections for noise rejection over distance.**

---
