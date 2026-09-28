---
id: skill-14-testing-and-qc-f5a19ed54d
purpose: 14 testing and qc
source: src/vibey_tools/skills/plugins/media-engineering/skills/media-captions-podcasts-rights-and-qc/SKILL.md
requires: ["skill-13-ai-generation-and-the-licensing-fight-8d9fcbfad2"]
links: []
---

## §14. Testing and QC

**[DURABLE] Media QC is its own discipline and most software teams underinvest in it.**

**Automated**: **file validation** against a spec (⚠️ **broadcast deliverables get rejected
for things like wrong audio channel order, missing bars and tone, or a two-frame black
gap** — validate before you ship); **loudness verification** (§6 → `media-production-and-loudness`); **PSNR/SSIM/VMAF** for
encode quality (⚠️ **VMAF is Netflix's perceptual metric and the current industry default —
and like all such metrics it can be gamed by tuning to it**); **black frame, freeze frame,
and silence detection**; **A/V sync measurement**; **caption presence and timing checks.**

**Tools**: **FFmpeg/FFprobe**, **MediaInfo**, **Bitmovin Analyzer**, **Hybrik**,
**Interra Baton**, **Telestream Vidchecker**, **libvmaf**.

**⚠️ And the irreplaceable step: watch and listen to it.** Automated QC catches spec
violations; **it does not catch a wrong audio track, an upside-down insert, or a grade that
looks wrong.** Golden-reference comparison and human spot checks remain necessary.

**⚠️ Test matrix reality**: browsers × devices × OS versions × codecs × DRM × network
conditions. **You cannot cover it exhaustively — pick your top device/browser combinations
by actual audience telemetry and cover those properly.**
