---
id: skill-security-b1e2d1e835
purpose: security
source: src/vibey_tools/skills/plugins/frontend-design/skills/nextjs-patterns/SKILL.md
requires: ["skill-performance-optimization-1cca419b17"]
links: ["skill-deployment-d1209b2eda"]
---

## Security

### CVE-2025-29927 (CVSS 9.1) — Middleware Auth Bypass

The `x-middleware-subrequest` header could bypass all middleware-based authorization. Published March 21, 2025; reported by Rachid Allam.

- **Patched in:** 12.3.5, 13.5.9, 14.2.25, 15.2.3
- **Not affected:** Vercel-hosted deployments
- **At risk:** Self-hosted (`next start`)
- **Architectural lesson:** Middleware is not a security boundary — auth must live in the DAL

### May 2026 Security Release (13 advisories)

Published May 6–7, 2026 — covering auth bypass, SSRF, cache poisoning, XSS, RSC denial-of-service (CVE-2026-23870).

- Original patches (15.5.16 / 16.2.5) were superseded after an incomplete fix
- **Pin to:** 15.5.18 / 16.2.6 for Turbopack users
- SSRF advisory (GHSA-c4j6-fc7j-m34r) affects only self-hosted deployments

### Rate Limiting

`@upstash/ratelimit` + Upstash Redis (sliding window) is the dominant pattern.

Key rules:
- A global 100 req/min cap is not endpoint security — set low, specific thresholds on the right assets
- In-memory Maps don't survive edge instances/redeploys; use external Redis
- Apply to: login, OTP, password reset, expensive/AI endpoints

### Input Validation and SSRF Prevention

- Validate all inputs server-side with Zod
- For SSRF: restrict/allowlist server-side fetch targets
- Validate `returnTo`/redirect params to relative URLs only (open-redirect/phishing prevention)

### Secrets

- Never expose via `NEXT_PUBLIC_` env vars (these are baked into the client bundle at build time)
- Use the `server-only` package to prevent accidental client import
- Use React taint APIs (`taintObjectReference`, `taintUniqueValue`) to prevent passing sensitive objects to Client Components
- Set `NEXT_SERVER_ACTIONS_ENCRYPTION_KEY` for consistent keys across instances

---
