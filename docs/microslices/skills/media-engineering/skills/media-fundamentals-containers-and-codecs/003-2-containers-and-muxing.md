---
id: skill-2-containers-and-muxing-aaa8195aa2
purpose: 2 containers and muxing
source: src/vibey_tools/skills/plugins/media-engineering/skills/media-fundamentals-containers-and-codecs/SKILL.md
requires: ["skill-1-fundamentals-ae976f3025"]
links: ["skill-3-codecs-dfc03fecbc"]
---

## §2. Containers and Muxing

**[DURABLE] The container is not the codec, and conflating them causes endless confusion.**
An `.mp4` can contain H.264, HEVC, AV1, AAC, or Opus. **"MP4 doesn't play" is almost never
about MP4.**

| Container | Use | ⚠️ Notes |
|---|---|---|
| **MP4 / ISOBMFF** | Universal delivery | The base for CMAF and fMP4 (§7 → `media-transcoding-streaming-and-drm`) |
| **fMP4 / CMAF** | ⚠️ **Streaming — the convergence format** | One set of segments serves both HLS and DASH |
| **MPEG-TS** | Broadcast, legacy HLS | Higher overhead; robust to corruption |
| **MKV / WebM** | Open, flexible | WebM is a Matroska subset |
| **MOV** | Apple production | ProRes lives here |
| **MXF** | Broadcast mastering | ⚠️ **Notoriously many incompatible flavours** |
| **WAV / AIFF** | Uncompressed audio | ⚠️ **WAV is 4 GB-limited unless RF64/BW64** |
| **FLAC / ALAC** | Lossless audio | |
| **Ogg** | Vorbis, Opus, Theora | |

**⚠️ The muxing details that bite**: **timestamps** — PTS (presentation) vs DTS (decode),
which differ whenever B-frames exist; **timescales** and rounding drift; **edit lists**
(⚠️ **an mp4 edit list can offset playback and many tools ignore it, producing A/V sync
differences between players**); **`moov` atom placement** — ⚠️ **at the end means the file
won't start playing until fully downloaded; `faststart` moves it to the front**, and this
is the single most common "why won't my MP4 stream" cause; and **sample entry codes** —
`avc1` vs `avc3`, `hvc1` vs `hev1` (⚠️ **the difference is whether parameter sets are in
the decoder config or inline, and Safari/FairPlay requires the former** — a real
interoperability trap).

---
