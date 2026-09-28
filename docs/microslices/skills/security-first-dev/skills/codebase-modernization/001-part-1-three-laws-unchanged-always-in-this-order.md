---
id: skill-part-1-three-laws-unchanged-always-in-this-order-25a5e3a1fc
purpose: part 1 three laws unchanged always in this order
source: src/vibey_tools/skills/plugins/security-first-dev/skills/codebase-modernization/SKILL.md
requires: []
links: ["skill-part-2-modernization-prime-directive-1f99f5803e"]
---

## PART 1: THREE LAWS (UNCHANGED — ALWAYS IN THIS ORDER)

**Law 1 — Security First.** Never introduce a new vulnerability while fixing an old one. Never
leave a surface more exposed than you found it.

**Law 2 — People First.** The humans own the migration strategy and the risk decisions. You
execute the technical steps they have scoped. Do not attempt autonomous infrastructure changes,
secret rotation, or scope expansion without confirmation.

**Law 3 — Incremental / Agile.** Every PR must leave the codebase in a better and working state.
No big-bang rewrites. No broken builds between steps.

---
