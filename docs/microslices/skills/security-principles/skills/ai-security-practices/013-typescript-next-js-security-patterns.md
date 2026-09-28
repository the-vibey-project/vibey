---
id: skill-typescript-next-js-security-patterns-29d8bad069
purpose: typescript next js security patterns
source: src/vibey_tools/skills/plugins/security-principles/skills/ai-security-practices/SKILL.md
requires: ["skill-python-security-patterns-acfb5f9875"]
links: ["skill-ai-model-supply-chain-llm03-2025-0f0cf804e1"]
---

## TypeScript / Next.js Security Patterns

### TypeScript as a Security Mechanism
- Strict types + Zod runtime validation at every trust boundary
- Strict schema validation also blunts prototype-pollution (reject `__proto__`/`constructor` keys) — the exact class CVE-2025-55182 abused

### Server Actions and RSC
- Server Actions deserialize client input — validate with Zod, treat as untrusted
- Never hardcode secrets in Server Action code (source-exposure CVE risk)
- CSRF protection for Server Actions invoked from forms: Next.js encrypts action IDs; set a persistent `NEXT_SERVER_ACTIONS_ENCRYPTION_KEY` across instances

### Auth.js v5 / NextAuth
- All env vars prefixed `AUTH_` (auto-inferred)
- `AUTH_SECRET` is mandatory
- **JWT sessions:** encrypted (JWE) in HttpOnly cookies; can't be revoked pre-expiry but Edge-compatible
- **Database sessions:** allow revocation/"sign out everywhere" but not Edge-compatible
- Split config: `auth.config.ts` (edge-safe) vs `auth.ts` (with adapter) so middleware stays Edge-compatible
- Always validate sessions server-side for sensitive ops, not just in middleware

### Cookie Security Flags
HttpOnly + Secure + SameSite + `__Host-` prefix

### Content Security Policy
- Start with `default-src 'self'`
- Prefer **nonce-based** CSP over `'unsafe-inline'`
- Libraries: **Nosecone** (Arcjet) / set headers in `proxy.ts`
- Also add: HSTS, X-Content-Type-Options, Permissions-Policy, X-Frame-Options/`frame-ancestors 'none'`
- Validate with Google CSP Evaluator

### Server vs Client Data Exposure
Most dangerous anti-pattern: passing whole DB rows from Server to Client Components.
- Pass only needed, sanitized fields
- Use `import 'server-only'`
- Taint APIs (`experimental_taintObjectReference`/`taintUniqueValue`)
- With Supabase/Postgres: Row-Level Security as a DB-layer backstop

### API Route Security
- Rate limiting (@upstash/ratelimit, Arcjet)
- Explicit CORS allow-lists
- Validate all inputs server-side with Zod

### Dependency Security
- `npm audit` as a blocking CI step; lockfile committed
- **Socket** for behavioral analysis on PRs
- Pin GitHub Actions to commit SHA, not tag (GhostAction lesson)
- Renovate/Dependabot auto-merge patch releases for next/react/react-dom

---
