---
id: skill-domain-4-data-layer-security-cosmosdb-postgresql-databricks-156b32d5f8
purpose: domain 4 data layer security cosmosdb postgresql databricks
source: src/vibey_tools/skills/plugins/security-first-dev/skills/cybersecurity-implementation/SKILL.md
requires: ["skill-domain-3-frontend-security-react-and-blazor-wasm-f10ec2aa95"]
links: ["skill-domain-5-ai-tool-security-claude-code-and-cursor-96de2a1c8a"]
---

## DOMAIN 4: DATA LAYER SECURITY (COSMOSDB, POSTGRESQL, DATABRICKS)

### Foundational — Managed Identity Access, Encryption Defaults

All three platforms encrypt data at rest with AES-256 by default and enforce TLS 1.2+ in
transit. The foundational security step is eliminating connection strings with keys.

**CosmosDB — assign Built-in Data Contributor role:**
```bash
az cosmosdb sql role assignment create \
  --account-name myCosmosAccount --resource-group myRG \
  --role-definition-id "00000000-0000-0000-0000-000000000002" \
  --principal-id "<managed-identity-principal-id>" --scope "/"
```

```csharp
var cosmosClient = new CosmosClient(
    "https://your-account.documents.azure.com:443/",
    new DefaultAzureCredential(),
    new CosmosClientOptions { ConnectionMode = ConnectionMode.Direct });
```

**Critical pitfall:** Azure control-plane roles like "Cosmos DB Account Contributor" do NOT
grant data-plane access. You must assign Cosmos DB's native data-plane RBAC roles separately.
Always include `readMetadata` permission or queries fail with 403.

**PostgreSQL — enable Entra ID auth, create Managed Identity principal:**
```sql
-- Run as Entra admin
SELECT * FROM pgaadauth_create_principal('<identity-name>', false, false);
GRANT ALL ON ALL TABLES IN SCHEMA public TO "<identity-name>";
```

**Databricks — Unity Catalog storage credentials with Managed Identity:**
```sql
CREATE STORAGE CREDENTIAL my_credential
WITH (AZURE_MANAGED_IDENTITY = '<managed-identity-resource-id>');
CREATE EXTERNAL LOCATION my_location
URL 'abfss://<container>@<storage-account>.dfs.core.windows.net/<path>'
WITH (STORAGE CREDENTIAL my_credential);
```

Databricks notebook secrets: `dbutils.secrets.get(scope="my-kv-scope", key="db-password")`.
Secret values are redacted in notebook output. Never hardcode credentials.

### Intermediate — PostgreSQL RLS Tenant Isolation, CosmosDB Partition Keys, Audit Logging

**PostgreSQL Row-Level Security — database-enforced multi-tenant isolation:**
```sql
CREATE TABLE tenant_data (
    id SERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL,
    data TEXT
);
ALTER TABLE tenant_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_data FORCE ROW LEVEL SECURITY; -- Apply even to table owners

CREATE FUNCTION current_tenant_id() RETURNS UUID AS $$
BEGIN
    RETURN NULLIF(current_setting('app.tenant_id', true), '')::UUID;
END;
$$ LANGUAGE plpgsql STABLE;

CREATE POLICY tenant_isolation ON tenant_data
    FOR ALL USING (tenant_id = current_tenant_id());
```

Set tenant context from .NET middleware before each request's DB operations:
```csharp
await using var cmd = conn.CreateCommand();
cmd.CommandText = "SET LOCAL app.tenant_id = @tenantId";
cmd.Parameters.AddWithValue("tenantId", tenantIdFromJwt);
await cmd.ExecuteNonQueryAsync();
```

**RLS is deny-by-default:** enabling it without policies blocks ALL access. Always index
`tenant_id` columns for performance.

**CosmosDB multi-tenant isolation** — hierarchical partition keys for large tenants:
```csharp
ContainerProperties properties = new(
    id: "events",
    partitionKeyPaths: new List<string> { "/tenantId", "/userId", "/sessionId" });
```

For many small tenants, use `tenantId` as the partition key (most cost-effective). For tenants
exceeding 20GB, use Hierarchical Partition Keys.

**pgAudit for PostgreSQL audit logging:**
```bash
az postgres flexible-server parameter set \
  --server-name myserver --resource-group myRG \
  --name pgaudit.log --value "WRITE,DDL"
```

Query audit logs: `AzureDiagnostics | where Message contains "AUDIT:" | where TimeGenerated > ago(1d)`

### Advanced — Customer-Managed Keys, Unity Catalog Column Security, Purview

**Disable key-based CosmosDB auth entirely to enforce RBAC:**
```bash
az cosmosdb update --name myaccount --resource-group myRG --disable-local-auth true
```

**Databricks Unity Catalog column-level security via masking functions:**
```sql
CREATE FUNCTION mask_email(email STRING) RETURNS STRING
RETURN CASE
  WHEN IS_ACCOUNT_GROUP_MEMBER('pii-readers') THEN email
  ELSE CONCAT('***', SUBSTRING(email, LOCATE('@', email)))
END;

ALTER TABLE customers ALTER COLUMN email SET MASK mask_email;
```

**Row filters:**
```sql
ALTER TABLE sales SET ROW FILTER filter_fn ON (region);
```

Use Unity Catalog for all data governance in Databricks. Never access data directly via storage
account keys — use service principals with Unity Catalog RBAC.

**Microsoft Purview** for cross-platform data classification: register CosmosDB (schema from
first 10 docs per container), PostgreSQL, and Unity Catalog (full metadata + lineage) in Purview
Data Map. Configure scanning schedules and apply sensitivity labels.

---
