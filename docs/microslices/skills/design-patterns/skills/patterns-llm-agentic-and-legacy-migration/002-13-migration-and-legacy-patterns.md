---
id: skill-13-migration-and-legacy-patterns-3cdd3c8ddc
purpose: 13 migration and legacy patterns
source: src/vibey_tools/skills/plugins/design-patterns/skills/patterns-llm-agentic-and-legacy-migration/SKILL.md
requires: ["skill-12-llm-and-agentic-patterns-ff50762ffc"]
links: []
---

## §13. Migration and Legacy Patterns

**Strangler Fig** — ⚠️ **the default for legacy replacement.** Route traffic through a
facade, replace behind it incrementally, retire the old system when nothing routes to it.
**Big-bang rewrites fail at a rate that should have settled this argument decades ago.**

**Branch by Abstraction** — introduce an abstraction over the thing you're replacing,
implement the new side behind it, switch, remove. **Lets large changes live on trunk.**

**Anti-Corruption Layer** (§7 → `patterns-architectural`) — translate at the boundary so a legacy or vendor model
doesn't infect yours.

**Also**: **parallel run** (⚠️ **run both and compare outputs before cutting over** —
the highest-confidence migration technique available and badly underused), **feature
toggles** (with a plan for removal — see §14 → `patterns-reference`), **expand-contract / parallel change** for
schema and API migration (add the new, migrate, remove the old — **the only safe way to
change a schema under live traffic**), **characterization tests** (capture current
behaviour before changing it, bugs included).
