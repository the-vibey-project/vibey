---
id: skill-staged-setup-recommendations-67e62b022d
purpose: staged setup recommendations
source: src/vibey_tools/skills/plugins/frontend-design/skills/nextjs-patterns/SKILL.md
requires: ["skill-anti-patterns-e78c541806"]
links: []
---

## Staged Setup Recommendations

**Stage 1 — Foundation (any new project):**
`create-next-app` (or `create-t3-app` for typed RPC + Prisma/Drizzle + Auth.js) on App Router, `src/` directory, TypeScript strict, Tailwind, ESLint. Feature-based structure from day one; establish a DAL.

**Stage 2 — Data and mutations:**
Server Actions with `next-safe-action` + Zod; `react-hook-form` + `zodResolver` on client; `useActionState`/`useOptimistic` for UX. Decide caching explicitly.

**Stage 3 — Auth and security hardening (before launch):**
Auth.js v5 with split edge/Node config; JWT + DB refresh token. Verify auth in middleware AND DAL AND every Server Action. Add `@upstash/ratelimit` to auth and expensive endpoints. Pin Next.js to a patched version.

**Stage 4 — Performance and scale:**
`next/image`, `next/font`, `next/script`, `next/dynamic`; bundle analysis with CI budgets; PPR/Cache Components for mixed static+dynamic pages. Target: LCP <2.5s, INP <200ms, CLS <0.1.

**Stage 5 — Deployment decision:**
Default Vercel for time-to-market. Re-evaluate self-hosting at ~10M+ requests/month, compliance/data-residency needs, or existing K8s platform.
