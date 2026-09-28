---
id: skill-15-anti-patterns-6687fe7888
purpose: 15 anti patterns
source: src/vibey_tools/skills/plugins/media-engineering/skills/media-reference/SKILL.md
requires: []
links: ["skill-16-contested-questions-47a13ea142"]
---

## §15. Anti-Patterns

| Anti-pattern | Why |
|---|---|
| Confusing container with codec | ⚠️ **"MP4 won't play" is almost never about MP4** (§2 → `media-fundamentals-containers-and-codecs`) |
| `moov` atom at the end of a streamed MP4 | ⚠️ **Won't start until fully downloaded. Use faststart** (§2 → `media-fundamentals-containers-and-codecs`) |
| Ignoring `avc1`/`avc3`, `hvc1`/`hev1` distinctions | Safari/FairPlay requires parameter sets in the config (§2 → `media-fundamentals-containers-and-codecs`) |
| Ignoring edit lists | Players disagree → A/V sync differences (§2 → `media-fundamentals-containers-and-codecs`) |
| Assuming DCI 4K and UHD are the same | 4096 vs 3840 (§1 → `media-fundamentals-containers-and-codecs`) |
| 8-bit for HDR or gradient-heavy content | Visible banding (§1 → `media-fundamentals-containers-and-codecs`) |
| Choosing a codec by efficiency table alone | ⚠️ **VVC is best-in-class with ~5% device support** (§3.2 → `media-fundamentals-containers-and-codecs`) |
| Single-codec delivery | You'll be multi-codec for years (§3.2 → `media-fundamentals-containers-and-codecs`) |
| Misaligned keyframes across ABR renditions | ⚠️ **Breaks clean switching** (§7 → `media-transcoding-streaming-and-drm`) |
| Separate TS and fMP4 packaging | CMAF serves both; halve your storage (§7 → `media-transcoding-streaming-and-drm`) |
| Fixed ABR ladder for all content | Per-title encoding is a substantial win (§7 → `media-transcoding-streaming-and-drm`) |
| Not keeping the mezzanine | You'll re-encode when the next codec lands (§7 → `media-transcoding-streaming-and-drm`) |
| **Mastering to −8 LUFS** | ⚠️ **Platforms turn it down; you lose dynamics for nothing** (§6 → `media-production-and-loudness`) |
| Peaking at 0 dBFS with no true-peak headroom | Inter-sample peaks clip after encoding (§6 → `media-production-and-loudness`) |
| Treating LUFS and LKFS as different units | They're the same (§6 → `media-production-and-loudness`) |
| Assuming 30 fps arithmetic on 29.97 material | ⚠️ **The classic timecode error** (§5.3 → `media-production-and-loudness`) |
| Mixing drop-frame and non-drop timecode | ~3.6 s/hour drift (§5.3 → `media-production-and-loudness`) |
| Editing long-GOP camera footage directly | Transcode to an intermediate (§5.1 → `media-production-and-loudness`) |
| Wrong LUT type or mismatched colour space | Silently misgrades; looks like a choice (§5.2 → `media-production-and-loudness`) |
| Allocation or locks in the audio callback | Hard real-time thread (§4 → `media-production-and-loudness`) |
| Sidecar captions only, no embedded | ⚠️ **CEA-608/708 survive transcoding; sidecars get lost** (§10 → `media-captions-podcasts-rights-and-qc`) |
| ASR captions with no human review | Legally insufficient in many contexts (§10 → `media-captions-podcasts-rights-and-qc`) |
| Treating captions as a launch-week task | Legally required in many jurisdictions (§10 → `media-captions-podcasts-rights-and-qc`) |
| DRM as anti-piracy | ⚠️ **Its function is contractual compliance** (§9 → `media-transcoding-streaming-and-drm`) |
| Shipping cenc only, or cbcs only | FairPlay needs cbcs; older deployments expect cenc (§9 → `media-transcoding-streaming-and-drm`) |
| Rebuilding your live stack on MoQ today | ⚠️ **Months from RFC; no settled killer use case** (§8.2 → `media-transcoding-streaming-and-drm`) |
| WebRTC for a million-viewer broadcast | Scales expensively (§8.1 → `media-transcoding-streaming-and-drm`) |
| RTMP for distribution | Ingest protocol; doesn't scale out (§8.1 → `media-transcoding-streaming-and-drm`) |
| Assuming podcast downloads mean listens | ⚠️ **IAB defines "download" technically; no playback telemetry** (§11 → `media-captions-podcasts-rights-and-qc`) |
| Prefix analytics without considering the dependency | It's on your critical download path (§11 → `media-captions-podcasts-rights-and-qc`) |
| Letting FFmpeg drop metadata | ⚠️ **Default behaviour; it's how royalties go unpaid** (§12 → `media-captions-podcasts-rights-and-qc`) |
| Inventing ISRCs | Validate, don't fabricate (§12 → `media-captions-podcasts-rights-and-qc`) |
| Confusing recording rights with composition rights | ⚠️ **The central structural fact in music rights** (§12 → `media-captions-podcasts-rights-and-qc`) |
| Assuming a platform's commercial-use terms equal copyright | ⚠️ **They are not the same thing** (§13.2 → `media-captions-podcasts-rights-and-qc`) |
| Accepting uploads with no AI provenance policy | ⚠️ **Deezer reports 44% of new uploads are AI-generated** (§13.2 → `media-captions-podcasts-rights-and-qc`) |
| Automated QC with no human viewing | Catches spec violations, not wrong content (§14 → `media-captions-podcasts-rights-and-qc`) |
| Optimizing directly for VMAF | It's gameable like any metric (§14 → `media-captions-podcasts-rights-and-qc`) |

---
