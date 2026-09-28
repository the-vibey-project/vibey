---
id: skill-testing-patterns-b52d23e80f
purpose: testing patterns
source: src/vibey_tools/skills/plugins/frontend-design/skills/nextjs-patterns/SKILL.md
requires: ["skill-typescript-patterns-3bcffc072b"]
links: ["skill-styling-39ddb79577"]
---

## Testing Patterns

| Layer                          | Tool                              | Notes                                              |
|--------------------------------|-----------------------------------|----------------------------------------------------|
| Unit (sync Server/Client Components, Server Actions as plain functions, Zod schemas) | Vitest + React Testing Library | Vitest **cannot render async Server Components** — push those to E2E |
| E2E (async RSC, auth flows, checkout, cookies/middleware) | Playwright | Configure `webServer`; preferred over Cypress     |
| Mocking                        | Vitest mocks for `next/navigation`, `next/headers` | Mocky Balboa for server-side network mocking in Playwright |

---
