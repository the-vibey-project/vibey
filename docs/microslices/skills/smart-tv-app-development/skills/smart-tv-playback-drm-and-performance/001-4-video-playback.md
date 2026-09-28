---
id: skill-4-video-playback-9bb7f7d810
purpose: 4 video playback
source: src/vibey_tools/skills/plugins/smart-tv-app-development/skills/smart-tv-playback-drm-and-performance/SKILL.md
requires: []
links: ["skill-5-drm-1fdcb204a4"]
---

## §4. Video Playback

### 4.1 The stack

```
manifest (HLS .m3u8 / DASH .mpd)
  → ABR ladder selection (bitrate/resolution/codec variants)
    → segment fetch → buffer management
      → demux → DECODE (hardware!) → render
        → DRM license acquisition + key handling (§5)
          → subtitles/captions, audio track selection, trick play
```

**[DURABLE] Use the platform's player.** On every TV platform, hardware-accelerated
decode is mandatory — software decode of 4K HEVC on TV silicon does not work. That means:
Roku's `Video` node, Android's **Media3/ExoPlayer**, AVPlayer on tvOS, and the
platform-specific **AVPlay** (Tizen) or media APIs on webOS. On web platforms, MSE/EME
exists but the vendor's native path is usually the one that gets hardware decode and DRM
right.

### 4.2 Formats and the ladder

- **HLS** (Apple-originating, dominant in the US, `.m3u8`) and **DASH** (`.mpd`, dominant
  in Europe). **CMAF** lets one set of segments serve both, which is the modern answer to
  "must I encode twice?"
- **Codecs**: H.264/AVC (universal baseline), HEVC/H.265 (4K/HDR, patent-encumbered),
  VP9, AV1 (decode support is real on newer sets and absent on older ones).
  **⚠️ Codec support varies by model year and by hardware tier within a model year.**
  Query capability at runtime; never assume.
- **HDR**: HDR10, HLG, Dolby Vision, HDR10+ — each with its own licensing and signalling.
- **Audio**: AAC, AC-3/E-AC-3, Dolby Atmos. **Loudness matters**: streaming/SSAI targets
  **−23 LUFS (EBU R128)**, US broadcast contexts **−24 LKFS (ATSC A/85)**. Mismatched
  loudness between content and ads is one of the most-complained-about defects in
  streaming.
- **Ladder design**: enough rungs to adapt smoothly, not so many that switching thrashes.
  Include a low rung that works on bad connections — a TV user with a weak 5 GHz signal
  is common.

### 4.3 The metrics that matter

**[DURABLE] TV video quality is measured by four numbers, and users feel all of them:**
| Metric | Target |
|---|---|
| **Startup time (time-to-first-frame)** | **< 2 s.** Certification programmes test this |
| **Rebuffer ratio** | < 0.5% of playback time |
| **Average bitrate / bitrate at start** | As high as the connection sustains |
| **Playback failure rate** | < 1% of attempts |

**⚠️ Startup time is where TV apps most often fail certification and lose users.**
Techniques: pre-warm the player, start the license request in parallel with the manifest
fetch, use a low-bitrate first segment then ramp, and **never do a cold cascade of
sequential network round trips** (auth → entitlement → manifest → license → first segment).
Parallelize what you can.

**Trick play** (FF/RW with thumbnails) requires an I-frame playlist or a sprite sheet of
thumbnails. Users expect it; implementing it late is painful.

**Captions and subtitles are not optional** (§14.1 → `smart-tv-monetization-certification-and-operations`) — WebVTT, TTML/IMSC, CEA-608/708 —
and must honour the **platform's** caption style settings, which the user set once in
system preferences and expects everywhere.

---
