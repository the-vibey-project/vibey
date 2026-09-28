---
id: skill-4-resource-hierarchy-and-organization-c86da8c67a
purpose: 4 resource hierarchy and organization
source: src/vibey_tools/skills/plugins/aws-gcp-azure-deep-dive/skills/hyperscaler-framing-responsibility-identity-and-hierarchy/SKILL.md
requires: ["skill-3-identity-and-access-where-they-genuinely-differ-a654d76446"]
links: []
---

## §4. Resource Hierarchy and Organization

```
AWS     Organization → OUs → ⚠️ ACCOUNTS → resources (with tags)
        ⚠️ The account is the blast radius. Multi-account is the standard pattern
        (Control Tower, Landing Zone). Per-env, per-team, per-workload accounts
AZURE   Mgmt Groups → ⚠️ SUBSCRIPTIONS → Resource Groups → resources
        ⚠️ The RESOURCE GROUP is a genuinely useful lifecycle unit AWS lacks —
        things created together, deleted together
GCP     Organization → Folders → ⚠️ PROJECTS → resources
        ⚠️ The project is both a billing boundary and an isolation boundary,
        which makes the model cleanly simple
```
**⚠️ The universal principle**: **environment separation should be at the strongest
isolation boundary available — separate accounts/subscriptions/projects for prod and
non-prod, not just separate tags or namespaces.** ⚠️ **Tag-based separation is a
convention, not a control.**
**Tagging/labelling** — ⚠️ **enforce it from day one via policy (SCP, Azure Policy, Org
Policy), because retrofitting tags across an existing estate is one of those projects
that never finishes** and **untagged spend is unattributable spend** (§14 → `hyperscaler-cost-reliability-iac-lock-in-and-migration`).
