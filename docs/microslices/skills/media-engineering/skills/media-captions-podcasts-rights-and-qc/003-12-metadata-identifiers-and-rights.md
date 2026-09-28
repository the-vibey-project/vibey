---
id: skill-12-metadata-identifiers-and-rights-1ea076bf16
purpose: 12 metadata identifiers and rights
source: src/vibey_tools/skills/plugins/media-engineering/skills/media-captions-podcasts-rights-and-qc/SKILL.md
requires: ["skill-11-podcast-infrastructure-edc2953ab9"]
links: ["skill-13-ai-generation-and-the-licensing-fight-8d9fcbfad2"]
---

## §12. Metadata, Identifiers, and Rights

**[DURABLE] Boring, unglamorous, and the thing that determines whether anyone gets paid.**

**Music identifiers**: **ISRC** (recording), **ISWC** (composition — ⚠️ **the
recording/composition split is the single most important structural fact in music
rights**), **UPC/EAN** (release), **IPI/CAE** (writer), **ISNI** (party).
**Video**: **EIDR** (⚠️ **the film/TV equivalent, and increasingly required by
distributors**), **Ad-ID** for advertising.

**Embedded metadata**: **ID3** (MP3), **Vorbis comments**, **MP4 atoms**, **BWF/iXML**
(broadcast wave, ⚠️ **which carries timecode and is how production audio syncs**),
**XMP** and **EXIF**.

**Rights infrastructure**: PROs (ASCAP, BMI, PRS, GEMA), the **MLC** in the US for
mechanicals, **DDEX** as the messaging standard between labels, distributors and DSPs
(⚠️ **and the thing you'll implement if you build a distribution system**), and
**Content ID / Audible Magic** for fingerprint-based identification.

**⚠️ The practical warning**: **metadata errors are how royalties go unpaid**, and they are
extremely common. **Validate ISRCs, don't invent them, and preserve metadata through your
transcode pipeline** — ⚠️ **FFmpeg drops most metadata by default unless you ask it not
to.**

---
