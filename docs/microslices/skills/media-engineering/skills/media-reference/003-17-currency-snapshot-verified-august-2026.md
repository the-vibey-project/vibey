---
id: skill-17-currency-snapshot-verified-august-2026-e331bdeb78
purpose: 17 currency snapshot verified august 2026
source: src/vibey_tools/skills/plugins/media-engineering/skills/media-reference/SKILL.md
requires: ["skill-16-contested-questions-47a13ea142"]
links: ["skill-18-the-canon-0d9127c84a"]
---

## §17. Currency Snapshot — verified August 2026

| Thing | Status as of Aug 2026 | Decay risk |
|---|---|---|
| **⚠️ AV2** | **AOMedia released AV2 v1.0 in 2026** (announced Sept 2025 for year-end 2025; v1.0 reported June 2026). **~30% better compression than AV1, royalty-free.** **dav2d** decoder project emerging. ⚠️ **Introduces ML-assisted coding tools**; targets AV1's weak spots — real-time, AR/VR, split-screen, screen content. **Devices expected from 2026; broader adoption 2027–28** | **High** |
| **AV1** | Established as the preferred next-gen OTT codec: **~15% additional efficiency over HEVC**, royalty-free, broad hardware decode in shipping TVs. Netflix expanded it into cloud gaming and is evaluating it for high-concurrency live. ⚠️ **Real-time workloads remain computationally problematic** | Medium |
| **⚠️ Codec adoption** | **NETINT 2026 State of Video Encoding survey (via Dan Rayburn): HEVC in production at 65%** (+20% planning), **AV1 in production at 17%** (+40% planning 2026). ⚠️ **Not market share; planned ≠ launched; survey distributed via an encoding-hardware vendor's channels, so likely over-represents encoder-evaluating organizations** | Medium |
| **⚠️ VVC / H.266** | Finalized July 2020; **~50% better than HEVC**. ⚠️ **2026 hardware decode footprint ~5% of consumer devices — no shipping mobile silicon, no browser support.** **Many essential patent holders remain outside both pools as of March 2026** (Apple, Google, Qualcomm, Samsung, Sony and others named). **Android 17 added native VVC support where hardware decoders exist** — not a software player. Traction in smart TVs, STBs, broadcast; **Brazil TV 3.0 and TikTok in China** cited | Medium |
| **⚠️ Media over QUIC** | IETF WG moving through **monthly draft revisions toward Working Group Last Call**; transport at **draft-17** in early 2026 with **Cisco, Google and Meta co-editors**. **Cloudflare MoQ relays across 330+ cities.** **Eleven vendors demoed interop at NAB 2026 (April).** Browser baseline **March 2026: Chrome, Firefox, Safari 26.4+** via WebTransport/HTTP-3. Formats: **CMSF** (CMAF/fMP4 via MSE, DRM via EME, ~0.5–1 s) and **MSF** (LOC raw frames via WebCodecs, <150 ms). One open-source implementation reports **200–300 ms in production**. ⚠️ **Still needs a defined killer use case; months from RFC** | **High** |
| **LL-HLS / LL-DASH** | Classic HLS **20–45 s**; low-latency variants **~2–6 s** in practice per NAB 2026 reviews (2–4 s under ideal tuning) | Low |
| **⚠️ AI music litigation** | **RIAA sued Suno and Udio June 2024**; damages sought **up to $150k/work**. **UMG–Udio settled Oct 2025**; **WMG–Udio and WMG–Suno settled Nov 2025** (Suno to ship licensed-only models, download limits by tier). ⚠️ **Sony has settled with neither; UMG still litigating against Suno.** Suno arguing **fair use**, citing **Bartz v. Anthropic** (June 2025: training on lawfully acquired books can be fair use; pirate sourcing is not). **Fact discovery to 30 Sept 2026, dispositive motions April 2027 — pushing a US fair-use ruling into 2027.** **German court ruled for GEMA against Suno.** Independent-artist class actions filed separately | **High** |
| **AI platform response** | **Deezer: 44% of new uploads AI-generated.** **Spotify "Verified by Spotify" badge for non-AI artists.** **Apple Music rejecting some AI submissions.** Licensing deals now span **Merlin and Kobalt** as the main doorway for independents; **Sony has licensed some AI ventures while still suing Suno and Udio** | **High** |

**Goes stale fastest:** §13 → `media-captions-podcasts-rights-and-qc` entirely, and §8.2 → `media-transcoding-streaming-and-drm`. **Essentially never stale:** §1 → `media-fundamentals-containers-and-codecs`, §2 → `media-fundamentals-containers-and-codecs`, §4 → `media-production-and-loudness`'s
real-time constraint, §5.3 → `media-production-and-loudness`, §6 → `media-production-and-loudness`'s mechanics, §10 → `media-captions-podcasts-rights-and-qc`, §12 → `media-captions-podcasts-rights-and-qc`, §15.

---
