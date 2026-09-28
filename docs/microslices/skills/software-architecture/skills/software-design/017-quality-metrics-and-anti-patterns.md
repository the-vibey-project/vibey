---
id: skill-quality-metrics-and-anti-patterns-f2e46a0ea3
purpose: quality metrics and anti patterns
source: src/vibey_tools/skills/plugins/software-architecture/skills/software-design/SKILL.md
requires: ["skill-legacy-brownfield-design-0fcfd11cf1"]
links: ["skill-refactoring-and-evolution-63da9eabd9"]
---

## Quality Metrics and Anti-Patterns

### Code Quality Metrics
- Cyclomatic complexity and cognitive complexity
- LCOM (Lack of Cohesion in Methods)
- Instability, abstractness, and distance-from-main-sequence (Martin's metrics, in Ford & Richards)
- SonarQube debt ratio / SQALE rating
- **DORA change failure rate** as a design-quality signal

### Code Smells (Fowler)
- **Bloaters:** God Class, Long Method, Long Parameter List
- **Change Preventers:** Shotgun Surgery (one change requires changes in many places), Divergent Change (one class changes for many reasons)
- **Couplers:** Feature Envy (method more interested in another class's data)

### Architecture Anti-Patterns
- **Big Ball of Mud:** No discernible structure; implicit, uncontrolled dependencies
- **Distributed Monolith:** Multiple services that must be deployed together — "the worst of both worlds"
- **Chatty Microservices:** Fine-grained calls that create excessive network overhead
- **Shared Database:** Multiple services accessing the same database schema, creating hidden coupling
- **Anemic Domain Model:** Business logic in service/transaction scripts rather than domain objects

### Over- and Under-Engineering
- **Over-engineering:** Enterprise abstractions in a startup, premature generalization, "pattern overload"
- **Under-engineering:** Domain logic in controllers, data access mixed into the domain layer

---
