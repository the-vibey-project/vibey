---
id: skill-11-implementation-bcd0d69bff
purpose: 11 implementation
source: src/vibey_tools/skills/plugins/signal-processing/skills/dsp-implementation-tools-and-testing/SKILL.md
requires: []
links: ["skill-12-tools-1df57576ad"]
---

## §11. Implementation

**[DURABLE] Where DSP theory meets the hardware budget.**

**Fixed point** — ⚠️ **still standard on MCUs, DSP chips, and in FPGA/ASIC.**
**Q notation** (Q15, Q31) describes where the binary point sits. **The failure modes**:
**overflow** (⚠️ **use saturating arithmetic — wraparound turns a loud sound into a
horrible one**), **underflow and loss of precision** in cascades, and ⚠️ **coefficient
quantization changing your filter's response — and in IIR, potentially its stability**
(§3.2 → `dsp-sampling-frequency-domain-and-filters`). **Always simulate in fixed point before committing to hardware.**

**⚠️ Denormals**: on some CPUs, arithmetic on denormal floats runs **orders of magnitude
slower**. In a decaying IIR filter this manifests as **CPU spikes when the signal goes
quiet** — a genuinely confusing symptom. **Enable flush-to-zero, or inject tiny dither.**

**Real-time constraints**: fixed block size, **⚠️ no allocation, no locks, and no
unbounded operations in the audio callback** — this is a hard-real-time thread, and a
`malloc` or a mutex in it produces dropouts. **Lock-free ring buffers** to communicate with
other threads. **Latency = block size + algorithmic delay + hardware buffering.**

**Hardware**: **SIMD** (⚠️ **DSP vectorizes exceptionally well — this is often a 4–8×
win**), **DSP cores** (TI C6000, ADI SHARC), **ARM CMSIS-DSP** on Cortex-M (⚠️ **and the
M4F/M7 DSP extensions make surprisingly capable audio possible on a microcontroller**),
**FPGA** for extreme throughput or determinism, and **GPU** for large batch or image work
(⚠️ **but usually the wrong answer for low-latency streaming audio because of transfer
overhead**).

---
