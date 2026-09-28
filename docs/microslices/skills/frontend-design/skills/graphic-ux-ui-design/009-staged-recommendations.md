---
id: skill-staged-recommendations-a9655d4c54
purpose: staged recommendations
source: src/vibey_tools/skills/plugins/frontend-design/skills/graphic-ux-ui-design/SKILL.md
requires: ["skill-anti-patterns-and-dark-patterns-be3fb0ce0d"]
links: []
---

## Staged Recommendations

**Stage 1 — Fix cheap, high-impact accessibility failures (weeks 1–4):**
Run axe/Lighthouse/WAVE; manually fix the six WebAIM categories: contrast (4.5:1 / 3:1 AA), alt text, form labels, empty links/buttons, document language. Add visible focus styles and skip links. Verify keyboard operability of every interactive element.

**Stage 2 — Standardize foundations as tokens (months 2–3):**
Establish three-tier token system; implement dark mode via semantic re-pointing (no pure black, elevation by lightness); set `max-width: 66ch` and `line-height: 1.5` on body; adopt 8pt grid; define button hierarchy + states + touch targets (≥44pt/48dp). Move to `oklch()` with sRGB fallbacks.

**Stage 3 — Apply pattern evidence to your context (ongoing):**
Top-aligned labels; inline-after-completion validation; skeletons for content loading, spinners for short actions; Load More/pagination for goal-driven lists, infinite scroll only for exploratory feeds; honor `prefers-reduced-motion`. Decide density deliberately (dense for pro tools, airy for consumer/onboarding).

**Stage 4 — Operationalize the design system (quarter 2+):**
Adopt SemVer; pick a governance model (centralized to start, federate as contributors mature); define a deprecation process with an explicit window; measure adoption (coverage + usage).

**Stage 5 — Pilot AI tooling without betting the system on it:**
Use for rapid prototyping and concept exploration; require a human accessibility/contrast pass before anything ships; re-evaluate tool choice quarterly.
