---
id: skill-13-ai-generation-and-the-licensing-fight-8d9fcbfad2
purpose: 13 ai generation and the licensing fight
source: src/vibey_tools/skills/plugins/media-engineering/skills/media-captions-podcasts-rights-and-qc/SKILL.md
requires: ["skill-12-metadata-identifiers-and-rights-1ea076bf16"]
links: ["skill-14-testing-and-qc-f5a19ed54d"]
---

## §13. AI Generation and the Licensing Fight

**[VERSIONED — the fastest-moving and most legally live material here.]**

**The tools**: music (Suno, Udio, and licensed platforms emerging from settlements), voice
(ElevenLabs and the cloning ecosystem), video (Sora, Runway, Veo, Kling), and mastering
and stem separation — ⚠️ **the last of which is genuinely uncontroversial and widely
adopted, because it's a tool applied to your own material.**

### 13.1 ⚠️ The music litigation, as of August 2026

**The RIAA sued Suno and Udio in June 2024** on behalf of all three majors, seeking
**statutory damages of up to $150,000 per infringed work.** What has happened since is
**a split, not a resolution:**

- **Universal settled with Udio (October 2025)** — upfront payment plus ongoing licensing,
  with a licensed platform announced.
- **Warner settled with Udio (November 2025) and with Suno (November 2025)** — the Suno
  deal bundled a licensing arrangement under which **Suno builds new models trained only on
  licensed catalogue**, adds download restrictions by tier, and (per reporting) acquired
  Warner's Songkick.
- **⚠️ Sony has not settled with either, and UMG continues against Suno.** Suno is fighting
  on **fair use**, leaning on the **Bartz v. Anthropic** reasoning that training on lawfully
  acquired works can be fair use while sourcing from pirate libraries is not.
- **Schedules have slipped**: reporting in mid-2026 put fact discovery closing
  **30 September 2026** and dispositive motions due **April 2027** in the Suno case,
  ⚠️ **pushing any US fair-use ruling into 2027.**
- **In Germany, a court ruled for GEMA against Suno**, finding training on GEMA's
  repertoire without a licence infringing.
- **Independent musicians filed separate class actions**, arguing the major-label
  settlements don't protect smaller rights holders.

> **⚠️ GOTCHA — the structural critique is worth taking seriously, whatever your view of
> the technology.** The observed pattern is **"launch, train, settle"**: operate using
> copyrighted material without permission, face suits only from those powerful enough to
> bring them, then legitimize through selective licensing — ⚠️ **while the work of
> creators without the resources to sue remains in the training data, uncompensated.**
> One analysis notes the emerging shape is **a two-tier regime where major labels cut
> deals and independent artists are left out**, and that **Merlin and Kobalt have become
> the main doorway for independents.**
>
> ⚠️ **And note Sony's position is not simple opposition** — it has licensed some AI music
> ventures and joined platform initiatives **while still suing Suno and Udio.**

### 13.2 What this means if you're building
**⚠️ Platform-side detection and labelling is now real infrastructure**: **Deezer reports
44% of new uploads are AI-generated**; **Spotify launched a "Verified by Spotify" badge
for non-AI artists**; **Apple Music has rejected some AI submissions.** **If you run a
platform that accepts uploads, provenance and disclosure are product requirements now, not
future ones.**

**⚠️ And the practical caution for anyone shipping AI-generated media**: **the commercial
rights a generation platform grants you in its terms are not the same thing as copyright a
court would recognize**, and the terms differ by subscription tier. **Read them, and get
advice before commercial release.** **This document is not legal advice and the situation
is actively moving.**

---
