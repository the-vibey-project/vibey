---
id: skill-10-captions-and-accessibility-21b26772b1
purpose: 10 captions and accessibility
source: src/vibey_tools/skills/plugins/media-engineering/skills/media-captions-podcasts-rights-and-qc/SKILL.md
requires: []
links: ["skill-11-podcast-infrastructure-edc2953ab9"]
---

## §10. Captions and Accessibility

**[DURABLE] Legally required in many jurisdictions, and routinely treated as an
afterthought.**

**Formats**: **WebVTT** (web standard), **TTML/IMSC** (broadcast and streaming, richer
styling), **SRT** (simple, ubiquitous, ⚠️ **no positioning or styling**), **SCC/CEA-608**
and **CEA-708** (⚠️ **embedded in the video bitstream itself, which is why they survive
transcoding when sidecar files don't — and why they're a pain to edit**), **SAMI**.

**⚠️ The distinctions that matter**: **captions include non-speech audio information and
speaker identification; subtitles assume you can hear.** **Open** captions are burned into
the picture; **closed** can be toggled. **Audio description** is a separate narration
track for blind users — ⚠️ **and it has its own mixing and legal requirements.**

**Compliance**: **FCC rules** in the US, **EN 301 549** and the **European Accessibility
Act** in the EU, **WCAG** for web. **⚠️ ASR-generated captions are cheap and legally
insufficient in many contexts** — accuracy requirements typically demand human review, and
"good enough to understand" is not the standard.

---
