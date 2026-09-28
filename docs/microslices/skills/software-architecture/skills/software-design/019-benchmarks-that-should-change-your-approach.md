---
id: skill-benchmarks-that-should-change-your-approach-4b199a0b89
purpose: benchmarks that should change your approach
source: src/vibey_tools/skills/plugins/software-architecture/skills/software-design/SKILL.md
requires: ["skill-refactoring-and-evolution-63da9eabd9"]
links: ["skill-cross-cutting-themes-53baf2e4b3"]
---

## Benchmarks That Should Change Your Approach

| Signal | Diagnosis | Response |
|---|---|---|
| "Release coordination manager" role appears | Distributed monolith | Stop splitting; re-modularize |
| >50% of a layer is pass-through with no logic | Unnecessary abstraction layer | Collapse the layer |
| Adding parameters and conditionals to preserve a shared abstraction | Wrong abstraction (Metz) | Inline back to duplication; re-derive |
| ADRs stop being written within a quarter | Operating model broken, not the format | Fix the operating model |
| Code duplication or two-week churn rises after AI-tool rollout | AI maintainability debt accumulating | Reinstate refactoring discipline and review gates |

---
