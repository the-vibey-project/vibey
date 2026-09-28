---
id: skill-part-3-eight-inviolable-security-principles-saltzer-schroeder-zero-trust-dae7dda65c
purpose: part 3 eight inviolable security principles saltzer schroeder zero trust
source: src/vibey_tools/skills/plugins/security-first-dev/skills/security-first-scrum/SKILL.md
requires: ["skill-part-2-prime-directive-before-writing-any-code-46114d242e"]
links: ["skill-part-4-spec-driven-development-7e7a48e97d"]
---

## PART 3: EIGHT INVIOLABLE SECURITY PRINCIPLES (SALTZER-SCHROEDER + ZERO TRUST)

These derive from Saltzer & Schroeder (1975), NIST SP 800-160, OWASP, and the Zero Trust model.
Every decision is measured against all eight. There are no exceptions.

**1. Least Privilege.** Every service, user, and process operates with the minimum permissions
necessary. In code: scope Cosmos DB roles precisely, scope JWT claims tightly, never use
`AllowAnyOrigin()`. The 2013 Target breach and 2020 SolarWinds compromise both trace directly to
violations of this principle.

**2. Fail-Safe Defaults.** Access is denied unless explicitly granted. Middleware must authenticate
before authorizing. Route groups not explicitly marked `.AllowAnonymous()` require auth. New API
endpoints are `[Authorize]` by default — removing auth requires explicit justification in code
comments.

**3. Defense in Depth.** No single control is sufficient. Authentication + Authorization + Input
Validation + Rate Limiting + Security Headers + Secret Management + Scanning — all layers are
required, never optional.

**4. Complete Mediation.** Every request to every resource is checked for authority on every
access. Never cache authorization decisions. Every API endpoint validates the JWT, checks the
scope, and checks resource-level ownership (BOLA prevention — OWASP API1).

**5. Open Design.** Security must not depend on obscurity. Never rely on hidden endpoints or
undocumented parameters. The only secret is the key; the design can be public.

**6. Economy of Mechanism.** Prefer simple, well-understood implementations. Complex security
code has complex failure modes. Use platform-native controls (`Microsoft.Identity.Web`,
`AddRateLimiter`) over hand-rolled equivalents.

**7. Separation of Privilege.** No single identity holds all-powerful access. Service accounts are
scoped. Admin roles are separate from reader roles. Managed Identities are per-service, never
shared.

**8. Psychological Acceptability.** Security controls must not require heroics. Automated pipeline
gates, pre-commit hooks, and clear error messages make security the path of least resistance.

### Zero Trust Operational Tenets

- All communication is secured regardless of network location — TLS everywhere, no exceptions.
- Access is granted per-session with dynamic policy evaluation — validate every token, every
  request.
- Assume breach — write defensive code that limits blast radius if any component is compromised.
- Never trust unverified data regardless of source — including data from other internal services,
  third-party APIs, and Azure infrastructure. All inputs are untrusted until validated.

### CIA Triad Awareness

Every feature touches at least one: Confidentiality (auth, RBAC, encryption), Integrity (input
validation, parameterized queries), Availability (rate limiting, retries, circuit breakers). When
tensions arise, surface the tradeoff — do not silently resolve it.

---
