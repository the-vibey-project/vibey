---
id: skill-critical-next-js-react-cves-2025-2026-64d6893eaf
purpose: critical next js react cves 2025 2026
source: src/vibey_tools/skills/plugins/security-principles/skills/ai-security-practices/SKILL.md
requires: ["skill-denial-of-wallet-llm10-2025-unbounded-consumption-0370c770f1"]
links: ["skill-python-security-patterns-acfb5f9875"]
---

## Critical Next.js / React CVEs (2025–2026)

### React2Shell RCE — CVE-2025-55182 / CVE-2025-66478 (CVSS 10.0)
- **Unauthenticated RCE** exploitable on a default `create-next-app`
- React Server Components deserialization vulnerability
- **Actively exploited in the wild within days of disclosure**
- Follow-on CVEs landed through April 2026: CVE-2025-55184, CVE-2025-55183, CVE-2025-67779, CVE-2026-23864, CVE-2026-23869

**Action:** upgrade to patched Next.js (15.x patched line / 16.1.2+ with React 19.1+); validate inputs at the data layer; never trust middleware alone for security.

### Middleware Auth-Bypass — CVE-2025-29927 (CVSS 9.1)
- Spoofed `x-middleware-subrequest` header bypassed middleware-based authorization entirely
- **Fix:** upgrade (≥15.2.3, ≥14.2.25, ≥13.5.9, ≥12.3.5) AND strip the header at the reverse proxy/WAF

**Architectural lesson (applies beyond this CVE):** never rely on middleware alone for auth — do "optimistic" cookie checks in middleware but full session validation in the Server Component/Route Handler/Data Access Layer. In Next.js 16, `middleware.ts` is renamed `proxy.ts`.

---
