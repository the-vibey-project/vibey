---
id: skill-7-transcoding-and-packaging-e3585de057
purpose: 7 transcoding and packaging
source: src/vibey_tools/skills/plugins/media-engineering/skills/media-transcoding-streaming-and-drm/SKILL.md
requires: []
links: ["skill-8-streaming-delivery-2380b0317f"]
---

## §7. Transcoding and Packaging

**[DURABLE] The pipeline shape is stable even as the components change:**
```
INGEST → VALIDATE → DECODE → PROCESS (scale, filter, colour)
       → ENCODE (ABR ladder, multi-codec) → PACKAGE (CMAF)
       → ENCRYPT (DRM) → ORIGIN → CDN → PLAYER
```

**The ABR ladder** — multiple renditions at different resolutions and bitrates.
⚠️ **Per-title encoding beats a fixed ladder substantially**, because content complexity
varies enormously. **Convex-hull / per-shot approaches go further.**

**⚠️ The packaging rules that break ABR if you get them wrong**: **all renditions must
share aligned keyframes/IDR positions** so the player can switch cleanly; **segment
duration** (typically 2–6 s) trades latency against CDN efficiency; **and CMAF lets one
set of segments serve both HLS and DASH**, which halves your storage and origin cost —
⚠️ **and is the main reason to package CMAF rather than separate TS and fMP4 outputs.**

**Tools**: **FFmpeg** (⚠️ **the substrate of essentially the entire industry — learn it**),
**GStreamer** (pipeline framework), **Shaka Packager** and **Bento4** (packaging),
**x264/x265/SVT-AV1/libaom/dav1d** (encoders and decoders), **MediaInfo** for inspection,
plus the cloud services (AWS MediaConvert/MediaLive, Google Transcoder, Mux, Bitmovin,
Cloudflare Stream).

**⚠️ Practical realities**: transcoding is **CPU/GPU-expensive and embarrassingly
parallel** — chunk it; **hardware encoders (NVENC, QSV, and dedicated ASICs) are far
faster and somewhat lower quality at a given bitrate than software** at slow presets;
**cache and reuse** rather than re-transcoding; **and store the mezzanine**, because you
will need to re-encode when a new codec arrives.

---
