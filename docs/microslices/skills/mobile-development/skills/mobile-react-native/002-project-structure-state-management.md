---
id: skill-project-structure-state-management-180c0db662
purpose: project structure state management
source: src/vibey_tools/skills/plugins/mobile-development/skills/mobile-react-native/SKILL.md
requires: ["skill-adopt-the-new-architecture-now-the-legacy-bridge-is-end-of-life-6bbddb0c0d"]
links: ["skill-navigation-0682fa5546"]
---

## Project structure & state management

- **Structure:** feature-first / domain-driven modularization.
- **Split server state from client state:**
  - **Server state** → TanStack Query / React Query v5 (caching, background refetch,
    `useInfiniteQuery` for pagination).
  - **Client state** → **Zustand** (lightweight global state, selective subscriptions);
    **Redux Toolkit + RTK Query** for large apps needing middleware/devtools/time-travel and
    offline-first optimistic-write pipelines; **Jotai** for atomic/scoped state.
- **Type safety:** TypeScript **strict mode** + **Zod** for runtime schema validation at API
  boundaries.
