---
id: skill-core-philosophy-7bc657bf23
purpose: core philosophy
source: src/vibey_tools/skills/plugins/software-architecture/skills/software-architecture/SKILL.md
requires: []
links: ["skill-architecture-style-decision-df0882945e"]
---

## Core Philosophy

**Start with a modular monolith, not microservices.** Roughly 80% of microservices benefits come from logical boundaries, not independent deployment. Extract services only when concrete signals appear: independent scaling needs, team coordination friction exceeding ~30–40 engineers, or regulatory isolation. The Prime Video case study (90% cost reduction by consolidating to a monolith) and CNCF 2024 data showing 42% of organizations consolidating microservices confirm the trend.

**Decision thresholds:**
- Modular monolith: team ~10–100 engineers, scale up to millions of users, fewer than ~5 platform engineers
- Microservices: team >~100 engineers, a component needs ~50x the compute of others, polyglot requirements, or PCI/regulatory isolation
- Cost reality: microservices infrastructure runs 3.75–6x higher than monoliths for equivalent functionality

**Enforcement matters more than the label.** A modular monolith only works with enforced module boundaries: public APIs per module, schema-per-module data ownership, and architecture tests (import-linter in Python, ESLint boundary rules / dependency-cruiser in TypeScript).

---
