---
id: skill-staged-recommendations-4d477ee724
purpose: staged recommendations
source: src/vibey_tools/skills/plugins/software-architecture/skills/software-design/SKILL.md
requires: ["skill-cross-cutting-themes-53baf2e4b3"]
links: ["skill-expert-s-diagnostic-questions-8f19f04847"]
---

## Staged Recommendations

### Stage 1 — Establish Cheap, High-Leverage Practices (Any Team Size)
1. Adopt **ADRs in source control** with the Nygard 5-section template; define explicitly *when required*, *who advises*, and *where they live*
2. Adopt the **C4 model** using Mermaid or Structurizr so diagrams are Git-versioned and stay near code
3. Default new systems to a **well-factored modular monolith** with module boundaries enforced by a fitness function in CI from day one
4. Extract to microservices only on concrete pain + operational maturity

### Stage 2 — Scale the Decision Process (Growing Org)
1. Introduce a lightweight **RFC/design-doc process** for medium+ features; async-first with time-boxed review
2. Replace any Architecture Review Board with the **architecture advice process** (Harmel-Law)
3. Use an architecture advisory forum for *conversations*, not approvals
4. Codify recurring decisions as **architectural principles + a tech radar**

### Stage 3 — Govern Evolution Automatically (Mature Org)
1. Map every accepted ADR to at least one **fitness function**; fail the build on drift
2. Use **DORA metrics** as a feedback signal on design quality
3. Treat **AI design assistance as a force multiplier with guardrails**: require human validation; monitor duplication/churn metrics

---
