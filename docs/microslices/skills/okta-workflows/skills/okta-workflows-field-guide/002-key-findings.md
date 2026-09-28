---
id: skill-key-findings-8d4ee09083
purpose: key findings
source: src/vibey_tools/skills/plugins/okta-workflows/skills/okta-workflows-field-guide/SKILL.md
requires: ["skill-tl-dr-05f51c8a04"]
links: ["skill-recommendations-c339ad9224"]
---

## Key Findings

1. Workflows performs **no implicit type conversion** in comparisons — the number one source of "why
   did my If/Else take the wrong branch" bugs.
2. Tables "Search Rows" (searchRows2) is **case-sensitive AND caps at 3,500 rows** regardless of the
   Limit field.
3. The Azure AD/Entra connector uses **delegated (not app-only)** permissions, **silently fails on
   mail-enabled security/distribution groups**, and has **three different record caps** across its
   cards.
4. Streaming and async loops trade memory safety for loss of control — **you cannot stop them
   mid-execution**.
5. **Flow throttling is now an automated platform feature** that will silently limit resource-heavy
   loop/table flows.
