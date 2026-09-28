---
id: skill-version-reality-as-of-june-2026-f687461bba
purpose: version reality as of june 2026
source: src/vibey_tools/skills/plugins/frontend-design/skills/nextjs-patterns/SKILL.md
requires: ["skill-core-principle-1af8bb4b9f"]
links: ["skill-architecture-and-project-structure-49107bf3a4"]
---

## Version Reality (as of June 2026)

| Version | Released         | Key change                                                        |
|---------|------------------|-------------------------------------------------------------------|
| v14     | —                | `fetch` cached by default; experimental PPR                       |
| v15     | Oct 21, 2024     | `fetch` **uncached by default**; cache opt-in required            |
| v16     | Oct 21, 2025     | Cache Components stable (`cacheComponents: true`, `use cache`); PPR is now default behavior when enabled; React Compiler 1.0 stable but **opt-in**; `middleware.ts` renamed to `proxy.ts` (Node.js runtime) |

**This is the #1 source of cache bugs.** Before debugging caching issues, always identify which major version the codebase is on.

---
