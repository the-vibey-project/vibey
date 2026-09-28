---
id: skill-ux-research-methods-d447f3d3aa
purpose: ux research methods
source: src/vibey_tools/skills/plugins/frontend-design/skills/graphic-ux-ui-design/SKILL.md
requires: ["skill-accessibility-and-inclusive-design-797cb256bc"]
links: ["skill-design-systems-a613791c3d"]
---

## UX Research Methods

### Method Selection by Question Type

| Phase      | Methods                                                       |
|------------|---------------------------------------------------------------|
| Generative/Discovery | User interviews, contextual inquiry, diary studies, JTBD |
| Evaluative  | Usability testing (moderated/unmoderated), tree testing      |
| IA          | Card sorting (open/closed/hybrid), tree testing              |
| Behavioral at scale | Analytics, heatmaps, session recordings (Hotjar, FullStory) |
| Quantitative UX | SUS, SUPR-Q, NPS                                        |

A/B testing works for high-traffic, isolatable changes with proper statistical significance. Misused for low-traffic pages or as a substitute for qualitative "why."

### Usability Benchmarks

**SUS (System Usability Scale):**
- Mean score across 446 studies: **68** (SD: 12.5) — this is the "C" / 50th percentile
- ≥80.3: "A" grade (top ~10–15%)
- <51: bottom ~15%
- SUS is not a percentage

**Cognitive laws (useful heuristics, not physics):**
- **Hick's Law**: decision time grows logarithmically with number/complexity of choices → argues for progressive disclosure and chunking, not blanket minimalism
- **Fitts's Law**: acquisition time depends on target size and distance → make primary targets big and close; make destructive actions small and far
- **Miller's Law ("7±2")**: frequently misused to justify arbitrary 7-item limits; the real lesson is chunking and recognition-over-recall, not capping menus at 7

**Nielsen's 10 Heuristics** — most commonly violated in practice:
1. Visibility of system status
2. Error prevention
3. User control and freedom (undo/escape)
4. Match between system and real world

### Information Architecture

- Card sorting + tree testing + sitemapping
- Generally favor breadth over depth for findability
- Design for both search AND browse
- Faceted navigation + a sound taxonomy is the backbone of e-commerce and large content sites

---
