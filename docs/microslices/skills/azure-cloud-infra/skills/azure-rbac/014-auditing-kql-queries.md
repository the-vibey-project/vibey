---
id: skill-auditing-kql-queries-b03929eed4
purpose: auditing kql queries
source: src/vibey_tools/skills/plugins/azure-cloud-infra/skills/azure-rbac/SKILL.md
requires: ["skill-best-practices-f274b432f9"]
links: []
---

## Auditing: KQL Queries

**Who assigned what role, when:**
```kql
AzureActivity
| where TimeGenerated > ago(30d)
| where OperationNameValue =~ "Microsoft.Authorization/roleAssignments/write"
| where ActivityStatusValue =~ "Start"
| extend props = parse_json(tostring(Properties_d.requestbody))
| extend RoleDef = tostring(props.Properties.RoleDefinitionId)
| extend PrincipalId = tostring(props.Properties.PrincipalId)
| project TimeGenerated, Caller, RoleDef, PrincipalId, ResourceId
```

**Detect all RBAC changes:**
```kql
AzureActivity
| where CategoryValue == "Administrative"
| where OperationNameValue in (
    "Microsoft.Authorization/roleAssignments/write",
    "Microsoft.Authorization/roleAssignments/delete")
| where ActivityStatusValue == "Succeeded"
| project TimeGenerated, Caller, OperationNameValue, ResourceId
| order by TimeGenerated desc
```

**Find unused custom roles:**
```kql
AuthorizationResources
| where type =~ "microsoft.authorization/roledefinitions"
| where tolower(tostring(properties.type)) == "customrole"
| extend rdId = tolower(id)
| join kind=leftouter (
    AuthorizationResources
    | where type =~ "microsoft.authorization/roleassignments"
    | summarize Count = count() by RoleId = tolower(tostring(properties.roleDefinitionId))
) on $left.rdId == $right.RoleId
| where isempty(Count)
| project RoleName = tostring(properties.roleName), rdId
```
