---
id: skill-twelve-highest-impact-actions-in-priority-order-87444ea524
purpose: twelve highest impact actions in priority order
source: src/vibey_tools/skills/plugins/security-first-dev/skills/cybersecurity-implementation/SKILL.md
requires: ["skill-domain-6-azure-infrastructure-and-devsecops-c998879c2a"]
links: []
---

## TWELVE HIGHEST-IMPACT ACTIONS (IN PRIORITY ORDER)

1. **Replace all connection-string-with-keys patterns with Managed Identity RBAC** — the single
   biggest attack surface reduction across the entire stack.
2. **Enforce Authorization Code + PKCE on all SPAs** while disabling implicit grant in app
   registrations.
3. **Deploy Private Endpoints** for every PaaS service (Key Vault, Cosmos DB, PostgreSQL,
   Databricks, Storage).
4. **Enable Microsoft Defender for Cloud** across all plans.
5. **Implement the DevSecOps pipeline** with quality gates that block on HIGH/CRITICAL findings.
6. **Deploy enterprise-managed settings** for Claude Code and Cursor with file deny rules.
7. **Add PostToolUse Semgrep hooks** to every repository's `.claude/settings.json`.
8. **Enable Key Vault RBAC, soft-delete, and purge protection** on every vault.
9. **Implement PostgreSQL RLS** for multi-tenant data isolation.
10. **Enable Unity Catalog** for all Databricks data governance with column masking on PII.
11. **Wire Gitleaks** with full git history scan (`fetch-depth: 0`) on every PR.
12. **Set `ClockSkew = TimeSpan.Zero`** and verify `UseAuthentication` precedes
    `UseAuthorization` in every .NET API.

The maturity tiers are not sequential gates — they represent increasing depth. A team can
implement Foundational across all six domains in the first sprint, then progressively deepen
into Intermediate and Advanced tiers over subsequent quarters.

Zero-secrets architecture through Managed Identity is the foundation everything else builds upon.
Without it, Key Vault references, Private Endpoints, and RBAC assignments are incomplete controls.
