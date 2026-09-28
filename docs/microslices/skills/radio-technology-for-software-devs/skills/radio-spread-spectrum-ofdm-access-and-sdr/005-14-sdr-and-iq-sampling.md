---
id: skill-14-sdr-and-iq-sampling-6577dfeb0e
purpose: 14 sdr and iq sampling
source: src/vibey_tools/skills/plugins/radio-technology-for-software-devs/skills/radio-spread-spectrum-ofdm-access-and-sdr/SKILL.md
requires: ["skill-13-multiple-access-cff0c792f0"]
links: ["skill-15-sampling-and-dsp-essentials-c59f03228b"]
---

## §14. ⚠️ SDR and IQ Sampling

**⚠️ The concept that makes radio tractable for software people, and the one most
tutorials explain badly.**

```
        ┌─────────┐   ┌──────┐   ┌─────┐   ┌──────────────┐
RF ────►│ LNA/Mix │──►│ Filt │──►│ ADC │──►│ YOUR SOFTWARE│
        └─────────┘   └──────┘   └─────┘   └──────────────┘
        ⚠️ hardware shrinks; software grows
```
**⚠️ IQ (complex baseband) is the key idea.** **The radio mixes the signal down so the
carrier is at 0 Hz, producing two streams: I (in-phase) and Q (quadrature, 90° shifted).**
⚠️ **Together they form a COMPLEX number per sample.**
**⚠️ Why complex, concretely:**
- ⚠️ **A real-valued signal cannot distinguish +10 kHz from −10 kHz relative to the
  carrier.** **The complex representation can, so you get the full spectrum around your
  tuned frequency rather than a folded-over version.**
- ⚠️ **Amplitude = |I + jQ|; phase = atan2(Q, I).** **Every modulation in §8 → `radio-antennas-propagation-noise-and-modulation` becomes
  arithmetic on complex numbers.**
- **A constellation diagram is literally a scatter plot of your IQ samples.**
- ⚠️ **Sample rate = the bandwidth you can see.** **A 2 Msps complex stream gives you
  2 MHz of spectrum, centred on your tuning frequency.**

**⚠️ Practical gotchas that will confuse you first time:**
- **⚠️ DC spike at centre frequency** — **an artefact of direct-conversion receivers (LO
  leakage), not a real signal.** **Tune slightly off-target to avoid burying your signal
  under it.**
- **⚠️ IQ imbalance produces mirror images of real signals** reflected about the centre.
- **⚠️ Automatic gain control will lie to you about absolute power.**
- **⚠️ Overflow/dropped samples**: **if your processing can't keep up, samples are simply
  lost, and the symptom is corrupt demodulation rather than an error message.**

---
