---
id: skill-architecture-as-a-continuous-concern-05f42ce907
purpose: architecture as a continuous concern
source: src/vibey_tools/skills/plugins/engineering-process/skills/sdlc-practices/SKILL.md
requires: ["skill-requirements-engineering-in-the-sdlc-f1b5518a27"]
links: ["skill-development-practices-709fe97ccf"]
---

## Architecture as a Continuous Concern

### Key Practices
- **Architecture Decision Records (ADRs)**: Nygard format or MADR; stored in-repo alongside code; version-controlled.
- **Fitness functions** (Ford/Parsons/Kua, *Building Evolutionary Architectures*): make architectural qualities testable in CI.
- **Spikes**: time-box architectural uncertainty.
- Tech debt identified and classified as a first-class backlog activity.

### Design Principles
- **SOLID, DRY, KISS, YAGNI** — applied with judgment; premature DRY/abstraction is itself a smell.
- **Clean Architecture**: dependency rule — dependencies point inward; frameworks are details.
- **DDD strategic**: bounded contexts, context maps, ubiquitous language.
- **DDD tactical**: aggregates, entities, value objects, domain events.
- **API-first/contract-first**: OpenAPI/AsyncAPI before implementation.

### Documentation
- **C4 model** (Simon Brown — Context/Container/Component/Code): with Structurizr; visualizes architecture at four levels of detail.
- **Docs-as-code**: version-controlled, reviewed, tested.
- Agile "just enough, just in time" — not big upfront design.

---
