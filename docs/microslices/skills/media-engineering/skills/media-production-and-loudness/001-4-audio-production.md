---
id: skill-4-audio-production-b8575d9dad
purpose: 4 audio production
source: src/vibey_tools/skills/plugins/media-engineering/skills/media-production-and-loudness/SKILL.md
requires: []
links: ["skill-5-video-production-fa47cb0483"]
---

## §4. Audio Production

**[DURABLE] The stack an audio engineer actually uses, and what a software engineer needs
to know to integrate with it.**

**DAWs**: Pro Tools (⚠️ **still the post-production and studio standard**), Logic, Ableton
Live, Reaper (⚠️ **cheap, scriptable, and beloved by engineers**), Cubase, FL Studio,
Studio One, Bitwig.

**Plugin formats** — ⚠️ **the interop layer, and a real engineering concern**:
**VST3** (cross-platform, Steinberg), **AU / AUv3** (Apple), **AAX** (Pro Tools only),
**LV2** (Linux/open), and **CLAP** — ⚠️ **the newer open format (Bitwig/u-he) with better
threading, modulation and note expression, gaining real traction.** **JUCE** is the
dominant framework for writing plugins across all of them.

**⚠️ The real-time constraint governs everything**: the audio callback is a hard real-time
thread. **No allocation, no locks, no file I/O, no logging.** Buffer size sets latency
(⚠️ **64 samples at 48 kHz ≈ 1.3 ms; 512 ≈ 10.7 ms**) and trades against CPU. **Lock-free
ring buffers** to talk to the UI thread.

**MIDI**: 7-bit values, note on/off, CC, and the ⚠️ **note-off-vs-velocity-zero
ambiguity**. **MIDI 2.0** adds 32-bit resolution, per-note controllers, and
bidirectional negotiation — ⚠️ **adoption is real but slow, and MIDI 1.0 remains the
lingua franca.** **MPE** gives per-note pitch and pressure over MIDI 1.0 and is widely
supported.

**Audio interfaces and drivers**: **ASIO** (Windows, low-latency, ⚠️ **and the reason
WDM/DirectSound is unusable for production**), **Core Audio** (macOS, excellent),
**ALSA/JACK/PipeWire** (Linux — ⚠️ **PipeWire has largely resolved the historic
JACK/PulseAudio split**). **Network audio**: **Dante** (⚠️ **the professional standard**),
AES67, AVB, NDI for video-plus-audio over IP.

---
