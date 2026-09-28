---
id: skill-1-fundamentals-ae976f3025
purpose: 1 fundamentals
source: src/vibey_tools/skills/plugins/media-engineering/skills/media-fundamentals-containers-and-codecs/SKILL.md
requires: ["skill-0-routing-18a337d382"]
links: ["skill-2-containers-and-muxing-aaa8195aa2"]
---

## §1. Fundamentals

**[DURABLE] The numbers that constrain everything downstream.**

**Audio**: **44.1 kHz** (CD, historical), **48 kHz** (⚠️ **the video and broadcast
standard — use this unless you have a reason not to**), 96/192 kHz in production.
**16-bit** for delivery, **24-bit or 32-bit float** for production (⚠️ **32-bit float
effectively eliminates clipping during recording, which is why modern field recorders use
it**). **Channel layouts**: mono, stereo, 5.1, 7.1, and object-based (Dolby Atmos,
which stores objects plus a bed rather than fixed channels).

**Video**: **frame rates** — 23.976, 24, 25, 29.97, 30, 50, 59.94, 60, 120.
⚠️ **The .976 and .97 rates are NTSC colour-subcarrier artifacts from 1953 and they are
still ruining timecode arithmetic today** (§5.3 → `media-production-and-loudness`). **Resolutions**: 1920×1080, 3840×2160
(UHD), 4096×2160 (DCI 4K — ⚠️ **not the same as UHD, and conflating them is a common
error**). **Chroma subsampling**: 4:4:4 (full), 4:2:2 (broadcast/production), **4:2:0**
(⚠️ **delivery standard — half the chroma resolution in both directions, and the reason
saturated red text looks bad in compressed video**). **Bit depth**: 8-bit (⚠️ **visible
banding in gradients**), 10-bit (HDR minimum), 12-bit.

**⚠️ Interlacing** is a 1930s bandwidth hack that will not die: 1080i is 1920×1080 in two
fields of 540 lines. **Deinterlacing is lossy and the artifacts are distinctive.** Progressive
everywhere you can.

**Colour**: **Rec. 709** (HD), **Rec. 2020** (UHD container), **DCI-P3**, **sRGB**.
**Transfer functions**: gamma for SDR, **PQ (SMPTE ST 2084)** and **HLG** for HDR.
**HDR formats**: HDR10 (static metadata), **HDR10+** and **Dolby Vision** (dynamic,
per-scene), HLG (broadcast-friendly, backwards-compatible-ish).

---
