---
id: skill-caveats-on-sources-4a67fc72c3
purpose: caveats on sources
source: src/vibey_tools/skills/plugins/quality-engineering/skills/debugging-and-observability/SKILL.md
requires: ["skill-quick-reference-decision-thresholds-1b12b8a372"]
links: []
---

## Caveats on Sources

- **Vendor-reported metrics are not independent.** Sentry's "94.5% accuracy," GitHub Copilot Autofix's timing improvements, and Pino's "7× faster than Winston" all come from vendors and controlled harnesses — treat as directional.
- **The "rubber duck fixes 56% more bugs" claim is unsupported.** No underlying study. The legitimate basis is the self-explanation literature (Chi et al., 1994).
- **Interruption-cost figures vary.** "23 minutes 15 seconds" is Gloria Mark's well-cited finding; downstream "50–100% more bugs" multipliers circulate in practitioner blogs without consistently traceable primary studies.
- **OpenRCA scores are evolving.** The 11.34% (2025, Claude 3.5) vs ~36% (2026, Claude Opus 4.6) gap reflects model improvement; some practitioners argue the benchmark's structure may overstate real-world readiness.
- **"Observability 2.0"** is a contested vendor framing; the three-pillars model remains widely and effectively used.
- **Chaos Monkey founding year:** Wikipedia dates invention to 2011, open-source release to 2012; some sources say 2010.
- Tool comparisons reflect the 2026 landscape; verify current pricing and feature tiers before committing.
