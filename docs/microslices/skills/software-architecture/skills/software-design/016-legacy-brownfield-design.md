---
id: skill-legacy-brownfield-design-0fcfd11cf1
purpose: legacy brownfield design
source: src/vibey_tools/skills/plugins/software-architecture/skills/software-design/SKILL.md
requires: ["skill-ai-impact-on-software-design-6285a65681"]
links: ["skill-quality-metrics-and-anti-patterns-f2e46a0ea3"]
---

## Legacy / Brownfield Design

### Before Redesigning
- **Characterization tests** — capture current behavior before changing anything
- **"Archaeology"** — understand what the system actually does before deciding what it should do
- Separate essential complexity from historical accident

### Migration Patterns
- **Strangler Fig:** Route traffic incrementally; new system grows around the old
- **Anticorruption Layer (ACL):** Protect the new bounded context from the legacy model's language and assumptions
- **Expand-and-contract:** Backward-compatible data/API evolution
- **Incremental over big-bang** — always; big-bang rewrites have a poor track record

### 2025 Emerging Technique
"GenAI for forward engineering" — AI-generated specifications of what legacy code *does* (hiding *how* it's implemented) as a modernization input. On Thoughtworks Radar as a technique to watch.

---
