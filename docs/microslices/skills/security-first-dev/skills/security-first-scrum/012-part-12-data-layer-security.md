---
id: skill-part-12-data-layer-security-984d1a5813
purpose: part 12 data layer security
source: src/vibey_tools/skills/plugins/security-first-dev/skills/security-first-scrum/SKILL.md
requires: ["skill-part-11-frontend-security-3693f41d54"]
links: ["skill-part-13-infrastructure-security-and-devsecops-a83108d32e"]
---

## PART 12: DATA LAYER SECURITY

### Cosmos DB — Managed Identity Access

```bash
# Assign Cosmos DB Built-in Data Contributor role
az cosmosdb sql role assignment create \
  --account-name myCosmosAccount --resource-group myRG \
  --role-definition-id "00000000-0000-0000-0000-000000000002" \
  --principal-id "<managed-identity-principal-id>" --scope "/"
```

**Critical pitfall:** Azure control-plane roles (e.g., "Cosmos DB Account Contributor") do NOT
grant data-plane access. You must assign Cosmos DB's native data-plane RBAC roles separately.
Always include `readMetadata` permission or queries fail with 403.

### PostgreSQL — Parameterized Queries Only

```csharp
// CORRECT
await using var cmd = new NpgsqlCommand(
    "SELECT * FROM users WHERE id = @id AND tenant_id = @tenantId", conn);
cmd.Parameters.AddWithValue("@id", userId);
cmd.Parameters.AddWithValue("@tenantId", tenantId);

// NEVER — string interpolation in SQL = SQL injection
// var cmd = new NpgsqlCommand($"SELECT * FROM users WHERE id = {userId}");
```

### Databricks — Unity Catalog and PII Masking

```sql
-- Column-level PII masking
CREATE FUNCTION mask_email(email STRING) RETURNS STRING
RETURN CASE
  WHEN IS_ACCOUNT_GROUP_MEMBER('pii-readers') THEN email
  ELSE CONCAT('***', SUBSTRING(email, LOCATE('@', email)))
END;
ALTER TABLE customers ALTER COLUMN email SET MASK mask_email;
-- Row-level security
ALTER TABLE sales SET ROW FILTER filter_fn ON (region);
```

Use Unity Catalog for all data governance. Never access data directly via storage keys.

### Secrets Sprawl Prevention

- 35% of private repositories contain secrets (GitGuardian 2025).
- Never commit secrets, even in private repositories.
- `.gitignore` must include: `.env`, `.env.*`, `*.pem`, `*.key`, `*.pfx`,
  `appsettings.Production.json`, `appsettings.Staging.json`, `secrets/`, `.azure/`, `.aws/`,
  `.ssh/`, `local.settings.json`, `launchSettings.json`.

---
