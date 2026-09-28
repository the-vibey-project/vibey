---
id: skill-5-video-production-fa47cb0483
purpose: 5 video production
source: src/vibey_tools/skills/plugins/media-engineering/skills/media-production-and-loudness/SKILL.md
requires: ["skill-4-audio-production-b8575d9dad"]
links: ["skill-6-loudness-62eb01dcd5"]
---

## §5. Video Production

**5.1 Acquisition and intermediates.** **Camera formats**: ProRes (⚠️ **the post-production
standard — cheap to decode, expensive in storage**), DNxHD/HR, **RAW** (BRAW, R3D, ARRIRAW
— ⚠️ **maximum flexibility, enormous files, and debayering cost**), and long-GOP camera
codecs (⚠️ **H.264/HEVC from a camera is painful to edit — transcode to an intermediate
first**). **Proxies** are standard practice: edit at low resolution, conform to full
resolution at the end.

**5.2 Colour.** **Log formats** (S-Log, C-Log, V-Log, Log C) preserve dynamic range for
grading. **LUTs** for transforms — ⚠️ **and a 1D LUT cannot do what a 3D LUT does; using
the wrong kind silently misgrades**. **ACES** is the standardized colour-managed pipeline.
⚠️ **The recurring bug: mismatched colour space or transfer function between stages,
producing washed-out or oversaturated output that looks like a grading choice rather
than an error.**

**5.3 ⚠️ Timecode — the most common source of "off by a few frames"**
**SMPTE timecode**, and the killer detail: **drop-frame vs non-drop-frame.**
At 29.97 fps, ⚠️ **drop-frame timecode skips frame *numbers* (never actual frames) to keep
clock time accurate — 2 numbers per minute, except every tenth minute.** Non-drop counts
sequentially and drifts ~3.6 seconds per hour against wall clock.
**⚠️ Mixing them, or assuming 30 fps arithmetic on 29.97 material, is the classic sync
error.** **Genlock and word clock** keep devices frame- and sample-aligned in a facility.

**5.4 Editing and delivery.** NLEs: Premiere, Final Cut, DaVinci Resolve (⚠️ **which
absorbed colour grading and audio into one application and changed the market**), Avid
Media Composer (broadcast/film standard). **Interchange**: EDL, AAF, XML, **OTIO**
(⚠️ **OpenTimelineIO — the open, scriptable interchange format, and the one worth knowing
if you're building tooling**). **Deliverables**: IMF for studio distribution, DCP for
cinema, and **broadcast spec sheets that will reject your file for reasons you did not
anticipate** (§14 → `media-captions-podcasts-rights-and-qc`).

---
