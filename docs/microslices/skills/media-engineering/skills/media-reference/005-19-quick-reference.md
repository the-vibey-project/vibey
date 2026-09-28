---
id: skill-19-quick-reference-de9d9140b5
purpose: 19 quick reference
source: src/vibey_tools/skills/plugins/media-engineering/skills/media-reference/SKILL.md
requires: ["skill-18-the-canon-0d9127c84a"]
links: ["skill-20-sources-and-method-8c1bd8af1c"]
---

## §19. Quick Reference

### 19.1 Numbers
- **48 kHz** audio for anything with video; **44.1** for music-only legacy
- **−23 LUFS** EBU R128 · **−24 LKFS** ATSC A/85 · **≈ −14 LUFS** typical streaming
  normalization ⚠️ **(verify per platform)**
- **−1 dBTP** true-peak ceiling, minimum
- **29.97 fps drop-frame skips 2 frame *numbers* per minute, except every 10th**
- **Segment duration 2–6 s**; keyframes must align across renditions
- **Classic HLS 20–45 s · LL-HLS/LL-DASH 2–6 s · WebRTC sub-second · MoQ 0.15–1 s**
- **AV1 ≈ 15% better than HEVC · AV2 ≈ 30% better than AV1 · VVC ≈ 50% better than HEVC**
- **VVC hardware decode ≈ 5% of consumer devices**

### 19.2 Picker
| Need | Use |
|---|---|
| Universal video compatibility | **H.264** baseline |
| Best royalty-free efficiency today | **AV1** |
| Apple-native, device capture | **HEVC** |
| Audio, best quality per bit | **Opus** |
| Audio, universal compatibility | **AAC** |
| Package once for HLS and DASH | **CMAF** |
| Live, huge scale, latency tolerable | **LL-HLS / LL-DASH** |
| Live, interactive, small audience | **WebRTC** |
| Live, sub-second at scale | ⚠️ **MoQ — prototype, don't bet** |
| Contribution over a lossy link | **SRT / RIST** |
| Premium content protection | **CENC + Widevine/PlayReady/FairPlay** |
| Captions on the web | **WebVTT** |
| Captions that survive transcoding | **CEA-608/708 embedded** |
| Podcast distribution | **RSS + enclosure. That's it** |
| Encode quality measurement | **VMAF** (⚠️ plus human review) |
| Anything at all | **FFmpeg** |

### 19.3 When it's broken
1. **`ffprobe` it.** Codec, container, timestamps, streams — most answers are here
2. **Check `moov` placement** if it won't start streaming (§2 → `media-fundamentals-containers-and-codecs`)
3. **Check keyframe alignment** if ABR switching stutters (§7 → `media-transcoding-streaming-and-drm`)
4. **Check PTS/DTS and edit lists** if A/V is out of sync (§2 → `media-fundamentals-containers-and-codecs`)
5. **Check timecode base** — 29.97 vs 30, drop vs non-drop (§5.3 → `media-production-and-loudness`)
6. **Check colour space and transfer function** if it looks washed out (§5.2 → `media-production-and-loudness`)
7. **Measure LUFS and dBTP** if it's quiet or clipping (§6 → `media-production-and-loudness`)
8. **Check DRM mode** — cenc vs cbcs — if playback fails on one platform (§9 → `media-transcoding-streaming-and-drm`)
9. **Check the device's actual codec support**, not the spec sheet (§3.2 → `media-fundamentals-containers-and-codecs`)

---
