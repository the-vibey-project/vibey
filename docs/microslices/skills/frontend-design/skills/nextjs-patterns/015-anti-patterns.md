---
id: skill-anti-patterns-e78c541806
purpose: anti patterns
source: src/vibey_tools/skills/plugins/frontend-design/skills/nextjs-patterns/SKILL.md
requires: ["skill-deployment-d1209b2eda"]
links: ["skill-staged-setup-recommendations-67e62b022d"]
---

## Anti-Patterns

| Anti-pattern                                        | Why it's wrong                                             |
|-----------------------------------------------------|------------------------------------------------------------|
| Over-using `'use client'`                           | Promotes subtrees, bloats bundles, breaks streaming/SEO    |
| `useEffect` for data that could be server-fetched   | Delays render, hurts LCP/SEO, creates waterfalls           |
| Reading `cookies()`/`headers()` in layouts          | Forces entire route dynamic, disables static/PPR           |
| N+1 queries                                         | Fetch in a loop; batch with `Promise.all`/DataLoader       |
| Trusting page-level auth for Server Actions         | Actions are separate public endpoints; re-verify each time  |
| Trusting TypeScript types at runtime                | Always validate with Zod                                   |
| Module-level global stores on the server            | Leaks state across requests                                |
| Fine-grained `revalidatePath` on everything         | Over-invalidation busts unrelated caches; use tags         |
| Assuming v14 caching in a v15/v16 codebase          | `fetch` is no longer cached by default                     |

---
