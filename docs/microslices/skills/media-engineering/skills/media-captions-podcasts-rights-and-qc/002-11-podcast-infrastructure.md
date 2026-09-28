---
id: skill-11-podcast-infrastructure-edc2953ab9
purpose: 11 podcast infrastructure
source: src/vibey_tools/skills/plugins/media-engineering/skills/media-captions-podcasts-rights-and-qc/SKILL.md
requires: ["skill-10-captions-and-accessibility-21b26772b1"]
links: ["skill-12-metadata-identifiers-and-rights-1ea076bf16"]
---

## §11. Podcast Infrastructure

**[DURABLE] Structurally the simplest media distribution system in this document, and
that's its strength.**

**RSS is the whole protocol.** An **RSS 2.0 feed with the iTunes namespace extensions** and
an `<enclosure>` pointing at an MP3 or AAC file. ⚠️ **There is no central platform — Apple
Podcasts, Spotify, Overcast and the rest all read the same feed**, which is why podcasting
stayed open when almost nothing else did.

**Podcasting 2.0 namespace** adds transcripts, chapters, funding tags, cross-app comments,
and value-for-value payments — ⚠️ **adopted by independent apps, largely ignored by the
big platforms.**

**⚠️ The engineering realities**: **measurement is defined by IAB Podcast Measurement
Technical Guidelines** (⚠️ **a "download" has a specific technical definition involving
byte thresholds and de-duplication windows — and unlike streaming there is no playback
telemetry unless the app volunteers it**); **dynamic ad insertion (DAI)** stitches ads at
request time, which means **the file is assembled per listener** and breaks naive caching;
**prefix-based analytics services** (⚠️ **which work by proxying every download and are
therefore a hard dependency on your critical path**); **hosting** (Libsyn, Buzzsprout,
Transistor, Megaphone); and **loudness** — ⚠️ **spoken-word targets sit around −16 LUFS
mono / −19 stereo in common guidance, and the platform normalization caveat in §6 → `media-production-and-loudness` applies.**

**Production practice**: multitrack recording per speaker (⚠️ **because you cannot
un-mix**), remote recording tools that record locally and upload (Riverside, SquadCast) to
avoid capturing network artifacts, and the standard chain — noise reduction, EQ,
compression, loudness normalization.

---
