---
id: skill-architecture-advice-process-6c5ac4a74a
purpose: architecture advice process
source: src/vibey_tools/skills/plugins/software-architecture/skills/software-design/SKILL.md
requires: ["skill-design-documents-and-rfcs-89d3b74c55"]
links: ["skill-fitness-functions-and-automated-governance-e5fe64ec6f"]
---

## Architecture Advice Process

### The 2024–2026 Shift Away from ARBs
**Architecture Review Boards are now considered counterproductive.**

Per Thoughtworks Technology Radar: "The State of DevOps report reveals that the traditional approach of Architecture Review Boards is counterproductive, often hindering workflow and **correlating with low organizational performance**."

### Harmel-Law's Architecture Advice Process (*Facilitating Software Architecture*, 2024)
> "Anyone can make any decision, as long as they seek **advice** (which is different from **permission**) from all affected parties and those with expertise."

The architect's role becomes **facilitation and curation of conversations**, not gatekeeping. Guardrails come from:
- Architectural principles
- A tech radar
- ADRs in source control

### Decision Frameworks
- **DACI:** Driver, Approver, Contributor, Informed — clarifies ownership without creating approval gates
- **Rough consensus** for technical decisions
- **Critique frameworks:** "I like, I wish, what if"

### Operating at Scale
- Use an **architecture advisory forum** for conversations, not approvals
- Codify recurring decisions as architectural principles + a tech radar
- If the same questions recur across RFCs → add a template field, not another gate
- If decisions stall → clarify decision ownership, don't add an approval gate

---
