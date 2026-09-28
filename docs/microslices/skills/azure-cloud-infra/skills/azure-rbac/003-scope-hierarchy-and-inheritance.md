---
id: skill-scope-hierarchy-and-inheritance-fbbd4ac8ec
purpose: scope hierarchy and inheritance
source: src/vibey_tools/skills/plugins/azure-cloud-infra/skills/azure-rbac/SKILL.md
requires: ["skill-control-plane-vs-data-plane-the-1-production-incident-source-858cc7ef54"]
links: ["skill-built-in-role-catalog-key-roles-1b7de826d2"]
---

## Scope Hierarchy and Inheritance

```
/providers/Microsoft.Management/managementGroups/<mgId>     ← management group
/subscriptions/<subId>                                       ← subscription
/subscriptions/<subId>/resourceGroups/<rgName>              ← resource group
/subscriptions/<subId>/resourceGroups/<rgName>/providers/   ← resource
  <provider>/<type>/<name>
```

Inheritance flows strictly downward. You **cannot break inheritance** the way NTFS permissions can be severed. The only mechanism to block inherited permissions is a **deny assignment**, which only Azure itself can create (via Deployment Stacks, managed applications, Service Fabric managed clusters).

### Hard limits (cannot be increased)
- 4,000 role assignments per subscription
- 500 role assignments per management group
- PIM eligible assignments do NOT count toward these limits
- Management group scope assignments do NOT count against per-subscription limits

---
