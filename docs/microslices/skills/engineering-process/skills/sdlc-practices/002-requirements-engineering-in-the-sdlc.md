---
id: skill-requirements-engineering-in-the-sdlc-f1b5518a27
purpose: requirements engineering in the sdlc
source: src/vibey_tools/skills/plugins/engineering-process/skills/sdlc-practices/SKILL.md
requires: ["skill-model-selection-d0917f5661"]
links: ["skill-architecture-as-a-continuous-concern-05f42ce907"]
---

## Requirements Engineering in the SDLC

### Types and Quality
Functional vs. non-functional (NFRs/quality attributes). Quality-attribute taxonomy: performance, scalability, availability, reliability, security, maintainability, usability, testability, observability, deployability.

**Critical rule**: NFRs must be specified concretely — "p99 latency < 200ms at 1,000 RPS," not "fast." NFRs are the most under-specified and highest-risk area in most software projects.

### Documentation Approaches
- **Traditional**: IEEE 830 SRS, Jacobson use cases, functional specs.
- **Agile**: user stories (As a/I want/So that) with **INVEST** (Independent, Negotiable, Valuable, Estimable, Small, Testable).
- **BDD** (Gherkin via Cucumber, SpecFlow, JBehave): builds shared dev/test/business language.
- **ATDD**: writes acceptance tests before implementation.
- **Impact mapping**: goal → actor → impact → deliverable.

### Backlog Management
- Refinement keeps stories ready; ruthless pruning counters "backlog obesity."
- **Prioritization**: MoSCoW, Kano, RICE (Reach × Impact × Confidence ÷ Effort), WSJF (cost of delay ÷ job size from SAFe).
- **Story mapping** (Jeff Patton): user journey backbone with release slices.
- Epic decomposition patterns: by workflow step, user role, data type, business rule, happy/unhappy path.

---
