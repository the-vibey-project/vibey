---
id: skill-3-codecs-dfc03fecbc
purpose: 3 codecs
source: src/vibey_tools/skills/plugins/media-engineering/skills/media-fundamentals-containers-and-codecs/SKILL.md
requires: ["skill-2-containers-and-muxing-aaa8195aa2"]
links: []
---

## §3. Codecs

### 3.1 Audio

| Codec | Position |
|---|---|
| **AAC** (LC, HE-AAC) | ⚠️ **The compatibility baseline. Everything plays it** |
| **Opus** | ⚠️ **Technically the best general-purpose choice** — speech to music, 6 kb/s to transparent; mandatory in WebRTC. Weaker in Apple/broadcast ecosystems |
| **MP3** | Legacy, universal, patents expired |
| **FLAC / ALAC** | Lossless distribution |
| **Dolby AC-3 / E-AC-3 / AC-4** | Broadcast and streaming surround |
| **Dolby Atmos / MPEG-H** | Object-based immersive |

### 3.2 ⚠️ Video — the 2026 landscape

**[VERSIONED, and this is where the most changed.]**

| Codec | Efficiency vs H.264 | Status |
|---|---|---|
| **H.264 / AVC** | baseline | ⚠️ **Still the compatibility floor. Everything decodes it** |
| **VP9** | ~HEVC-ish | Google-ecosystem; central to YouTube, limited elsewhere |
| **HEVC / H.265** | ~50% better | ⚠️ **Mature production footprint; Apple's preference; patent-pool complexity** |
| **AV1** | ~50%+, ~15% over HEVC | ⚠️ **Royalty-free, and now the preferred next-gen OTT codec** |
| **VVC / H.266** | ~50% over HEVC | Technically superb; ⚠️ **almost no hardware footprint** |
| **AV2** | ~30% over AV1 | ⚠️ **v1.0 released 2026. Royalty-free** |

**⚠️ The adoption reality is not the efficiency table.** A 2026 encoding survey found
**HEVC in production at ~65% of responding organizations (another 20% planning), against
AV1 at ~17% in production with ~40% planning deployment during 2026** — ⚠️ **note these are
not market-share figures, planned deployments aren't launches, and the survey was
distributed through an encoding-hardware vendor's channels, so it likely over-represents
organizations already evaluating encoders.** The pattern is still informative: **HEVC has
the mature footprint, AV1 has the momentum.**

> **⚠️ GOTCHA — VVC is the cautionary tale, and the lesson generalizes.** VVC is
> technically the strongest codec available: **~50% better than HEVC**, finalized July 2020.
> But as of 2026 its **hardware decode footprint is roughly 5% of consumer devices** —
> a few high-end TVs and set-top boxes, **no shipping mobile silicon, no browser support** —
> against AV1's broad presence. And **many essential patent holders remain outside both
> licensing pools**, leaving the royalty position unresolved.
>
> **Android 17 added native VVC support on devices with compatible hardware decoders** —
> ⚠️ **but that's exposing hardware decode that may exist, not shipping a software player,
> and Google is otherwise firmly in the AV1/AV2 camp.**
>
> **The likely equilibrium through the late 2020s: AV1 rules web streaming, HEVC remains
> the workhorse for device capture and Apple workflows, and VVC finds a professional and
> broadcast niche rather than mainstream ubiquity.** ⚠️ **A reminder that the best
> technology doesn't always win — the economics favoured a free competitor.**

**[VERSIONED] AV2 arrived**: AOMedia released **AV2 v1.0 in 2026**, ~30% better compression
than AV1, still royalty-free, with the **dav2d** decoder project filling the
implementation gap. ⚠️ **It introduces ML-assisted coding tools — a structural shift in
codec design philosophy — and targets AV1's weak spots: real-time workloads, AR/VR,
split-screen, and screen content.** **Devices are expected from 2026 with broader adoption
2027–28**, so treat it as a roadmap item, not a deployment decision.

**⚠️ And the AV1 caveat worth knowing**: it works extremely well for VOD and archival;
**for real-time workloads the computational overhead is still problematic.**

**[DURABLE] The practical answer is multi-codec delivery.** Encode H.264 as the floor, add
HEVC and/or AV1 for capable devices, and let the manifest and device capabilities decide.
**⚠️ You will be running at least two codecs for years.**

### 3.3 The encoding knobs that matter
**CRF/CQ vs. bitrate targeting** (⚠️ **CRF for VOD where you want consistent quality;
capped-CRF for streaming**), **preset** (⚠️ **the direct compute-vs-efficiency dial**),
**GOP length and keyframe placement** (⚠️ **must align with your segment duration or ABR
switching breaks** — §7 → `media-transcoding-streaming-and-drm`), **B-frames**, **two-pass vs. single-pass**, and
**per-title/per-shot encoding** — ⚠️ **which Netflix popularized and which yields real
savings because an animation and a sports broadcast need very different bitrates for the
same perceived quality.**
