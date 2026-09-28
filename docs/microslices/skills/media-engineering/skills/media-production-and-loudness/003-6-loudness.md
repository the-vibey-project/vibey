---
id: skill-6-loudness-62eb01dcd5
purpose: 6 loudness
source: src/vibey_tools/skills/plugins/media-engineering/skills/media-production-and-loudness/SKILL.md
requires: ["skill-5-video-production-fa47cb0483"]
links: []
---

## §6. Loudness

**[DURABLE] The single most practically useful section for anyone shipping audio, and the
one most often discovered too late.**

**⚠️ Peak level and perceived loudness are different things.** A track can peak at 0 dBFS
and sound quiet, or peak at −6 and sound crushed. **The loudness war** — decades of
ever-heavier compression to sound louder than the competition — **was ended not by taste
but by normalization.**

**The standards**: **ITU-R BS.1770** defines the measurement (K-weighted, gated).
**EBU R128** (Europe) targets **−23 LUFS integrated** with a max true peak of −1 dBTP;
**ATSC A/85** (US broadcast) targets **−24 LKFS**. ⚠️ **LUFS and LKFS are the same unit
with different names.**

**⚠️ The units to keep straight**: **Integrated LUFS** (whole-programme average),
**short-term** (3 s), **momentary** (400 ms), **LRA** (loudness range),
and **True Peak (dBTP)** — ⚠️ **which measures the inter-sample peaks that appear after
D/A conversion or lossy encoding, and is why a file that peaks at exactly 0 dBFS can clip
on playback.** Leave −1 dBTP of headroom minimum.

> **⚠️ GOTCHA — this is why your master sounds quiet on streaming.** **Every major platform
> normalizes playback loudness**, typically in the region of **−14 LUFS**, though **targets
> differ by platform and change without announcement.** If you master to −8 LUFS, the
> platform **turns it down** — and you've spent your dynamic range for nothing, arriving
> quieter *and* more crushed than a competitor who mastered sensibly.
>
> ⚠️ **Do not master to a platform target as a hard number.** Master for the music, keep
> true peak headroom, and check the integrated value. **Verify current targets per platform
> at release time rather than trusting any figure — including the one in this document.**
