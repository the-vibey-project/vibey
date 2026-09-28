---
id: skill-architecture-decision-records-adrs-049a181753
purpose: architecture decision records adrs
source: src/vibey_tools/skills/plugins/software-architecture/skills/software-design/SKILL.md
requires: ["skill-domain-driven-design-ddd-ea51814190"]
links: ["skill-the-c4-model-simon-brown-74f8e07a56"]
---

## Architecture Decision Records (ADRs)

### The Standard Format (Nygard, 2011)
ADRs are the single highest-ROI design practice. Store them **in source control next to the code** (Thoughtworks 2016 recommendation).

Five sections:
1. **Title** — Short noun phrase
2. **Status** — Proposed / Accepted / Deprecated / Superseded
3. **Context** — The forces at play; the problem
4. **Decision** — The response to those forces
5. **Consequences** — What becomes easier or harder; accepted trade-offs

One decision per record.

### Variants
- **MADR (Markdown Architectural Decision Records):** Adds decision drivers and considered options with pros/cons — better for genuinely contested decisions
- **Y-Statements (Zimmermann):** Concise one-sentence format: "In the context of [situation], facing [concern], we decided [option], to achieve [quality], accepting [downside]."

### The Operating Model — Most ADR Practices Die Without It
Teams pick a format but never decide:
- **When** an ADR is required (decisions that are hard to reverse OR wide in blast radius)
- **Who** advises (all affected parties + those with domain expertise)
- **Where** it lives (same repo, architecture/ directory, or decision log)

Without an explicit operating model, the practice dies within a quarter.

### Tooling
adr-tools, Log4brains, dotnet-adr, docToolchain, Structurizr

---
