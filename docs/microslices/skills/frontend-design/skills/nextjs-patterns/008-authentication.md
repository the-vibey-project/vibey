---
id: skill-authentication-bac6dacddc
purpose: authentication
source: src/vibey_tools/skills/plugins/frontend-design/skills/nextjs-patterns/SKILL.md
requires: ["skill-state-management-581ec0a9f1"]
links: ["skill-typescript-patterns-3bcffc072b"]
---

## Authentication

### Auth.js v5

Single `auth.ts` config exports `{ auth, handlers, signIn, signOut }`. Universal `auth()` works in Server Components, Route Handlers, and middleware.

**Split config for edge compatibility:**
- `auth.config.ts` — edge-safe, no DB adapter; used in middleware for JWT verification
- `auth.ts` — Node.js runtime, with DB adapter for session storage

### Sessions: JWT vs. Database

| Strategy       | Pros                                | Cons                              |
|----------------|-------------------------------------|-----------------------------------|
| JWT            | Stateless, edge-verifiable, fast   | Hard to revoke                    |
| Database       | Revocable, single source of truth  | DB call per request; edge can't reach most DBs |

Common middle ground: short-lived JWT (~15 min) + refresh token in DB.

**Always store session tokens in `httpOnly`, `secure`, `sameSite` cookies — never localStorage (XSS).**

### Defense in Depth: Three Layers

1. **Middleware/proxy** — optimistic route filtering (fast, edge); NOT a security boundary (CVE-2025-29927)
2. **Server Components / Route Handlers** — verify for data access
3. **Server Actions** — verify before every mutation

UI role checks are UX, not security. Include API routes in the middleware matcher (common bug: protecting `/dashboard` but leaving `/api/dashboard/*` open).

---
