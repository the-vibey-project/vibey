---
id: skill-20-sources-and-method-8c1bd8af1c
purpose: 20 sources and method
source: src/vibey_tools/skills/plugins/media-engineering/skills/media-reference/SKILL.md
requires: ["skill-19-quick-reference-de9d9140b5"]
links: []
---

## §20. Sources and Method

**Method.** Narrative review, written as engineering guidance for people building media
systems, and deliberately complementary to a DSP reference (algorithms) and a smart-TV
reference (app platforms). **§1 → `media-fundamentals-containers-and-codecs`, §2 → `media-fundamentals-containers-and-codecs`, §4 → `media-production-and-loudness`'s constraints, §5 → `media-production-and-loudness`, §6 → `media-production-and-loudness`'s mechanics, §10 → `media-captions-podcasts-rights-and-qc`, §11 → `media-captions-podcasts-rights-and-qc`, §12 → `media-captions-podcasts-rights-and-qc`,
§14 → `media-captions-podcasts-rights-and-qc` and §15 are stable** — container semantics, timecode, loudness measurement, caption
formats and identifier schemes have been settled for years and rest on the standards and
the practitioner literature rather than on anything searched. Three targeted searches were
run in **August 2026** on the layers that genuinely moved: the codec landscape, delivery
protocols, and the AI rights fight.

**Search log** (August 2026): AV1/AV2/VVC/HEVC adoption and licensing · Media over QUIC,
LL-HLS and low-latency streaming · Suno/Udio litigation, settlements, and AI music
licensing.

**Primary and near-primary sources consulted (selected):**
- **Codecs**: *Streaming Media*'s "State of Streaming Codecs 2026" and Jan Ozer's
  analysis; the **NETINT 2026 State of Video Encoding survey** as summarized by Dan
  Rayburn; AOMedia's AV2 announcements; multiple 2026 VVC guides for the hardware-footprint
  and patent-pool position
- **MoQ**: the **Fraunhofer FOKUS** MoQ page for the data model and the CMSF/MSF format
  split, **Streaming Learning Center** (Jan Ozer) and *The Register* for the NAB 2026
  interop and standardization state, plus vendor engineering write-ups from Wowza,
  Cloudflare-adjacent sources and Qualabs
- **AI music litigation**: **Music Business Worldwide** and **Reuters** for the settlement
  terms, **Chartlex's** litigation and licensing trackers for the case-by-case status, and
  a **Forbes** analysis for the "launch, train, settle" structural critique

**Confidence statement.** **High confidence** in §1 → `media-fundamentals-containers-and-codecs`, §2 → `media-fundamentals-containers-and-codecs`, §5 → `media-production-and-loudness`, §6 → `media-production-and-loudness`, §10 → `media-captions-podcasts-rights-and-qc`, §11 → `media-captions-podcasts-rights-and-qc`, §12 → `media-captions-podcasts-rights-and-qc` and §14 → `media-captions-podcasts-rights-and-qc` —
these are standards and long-settled practice. **High confidence in the MoQ technical
description** (§8.2 → `media-transcoding-streaming-and-drm`), which comes from Fraunhofer's implementation documentation and the
IETF working group's own materials. **Moderate confidence in §3.2 → `media-fundamentals-containers-and-codecs`'s adoption figures**: the
survey is explicitly self-selecting (⚠️ **and I have flagged its distribution channel in
both §3.2 → `media-fundamentals-containers-and-codecs` and §17 rather than presenting the numbers as market share**), and the
VVC device-support figure comes from a single 2026 analysis.

⚠️ **Lower confidence, and deliberately hedged, on two things.** **The AV2 release date**
— sources place v1.0 variously at year-end 2025 (as announced) and June 2026 (as reported),
which I have noted rather than resolved; **verify against AOMedia directly** before
relying on it. And **§13 → `media-captions-podcasts-rights-and-qc`'s litigation status is the fastest-decaying material in this
document**: settlement terms are largely private, case schedules have already slipped
once, court reporting varies in accuracy (⚠️ **I encountered conflicting attributions of
which judge is hearing the Suno summary-judgment motion, which is why I have not named
one**), and **any US fair-use ruling now appears to land in 2027.** §13 → `media-captions-podcasts-rights-and-qc` is **not legal
advice**; anyone with money or a release at stake should take proper advice, and §16.6's
ethical question is separate from whichever way the legal one resolves.
