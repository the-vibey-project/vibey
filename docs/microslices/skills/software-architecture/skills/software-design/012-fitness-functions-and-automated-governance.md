---
id: skill-fitness-functions-and-automated-governance-e5fe64ec6f
purpose: fitness functions and automated governance
source: src/vibey_tools/skills/plugins/software-architecture/skills/software-design/SKILL.md
requires: ["skill-architecture-advice-process-6c5ac4a74a"]
links: ["skill-api-design-a88fb9e9ea"]
---

## Fitness Functions and Automated Governance

### What Fitness Functions Are
From Ford, Parsons, Kua (*Building Evolutionary Architectures*, 2nd ed. 2023):
> "Any mechanism that performs an objective integrity assessment of some architecture characteristic."

Implemented as build-failing tests that enforce dependency direction, cycle-freedom, and layer rules.

### Tooling by Ecosystem
| Tool | Language | Enforces |
|---|---|---|
| **ArchUnit** | Java (gold standard) | Package dependencies, layer rules, naming conventions |
| **NetArchTest** | .NET | Namespace dependencies, layer rules |
| **dependency-cruiser** | JavaScript/TypeScript | Module dependency rules, cycle detection |
| **go-arch-lint** | Go | Package dependency rules |
| **jMolecules** | Java | DDD building blocks as annotations |

### The 2026 Frontier
- LLM-based fitness functions that check PR diffs against ADR-derived violation prompts
- MCP (Model Context Protocol) as an anticorruption layer for "agentic architecture governance"

### Governance Operating Model
1. Map every accepted ADR to at least one fitness function
2. Fail the build on architectural drift
3. Track tolerable-violation counts; ratchet them down over time
4. Use **DORA metrics** (especially change failure rate) as a feedback signal on design quality

> **Benchmark:** If code duplication or two-week churn rises materially after AI-tool rollout → reinstate refactoring discipline and review gates.

---
