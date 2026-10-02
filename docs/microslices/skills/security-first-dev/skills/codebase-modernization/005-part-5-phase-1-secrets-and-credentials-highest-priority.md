---
id: skill-part-5-phase-1-secrets-and-credentials-highest-priority-ac4986459e
purpose: part 5 phase 1 secrets and credentials highest priority
source: src/vibey_tools/skills/plugins/security-first-dev/skills/codebase-modernization/SKILL.md
requires: ["skill-part-4-phase-0-codebase-assessment-run-before-touching-anything-8b8d8c01be"]
links: ["skill-part-6-phase-2-authentication-and-authorization-migration-c1fc0705c7"]
---

## PART 5: PHASE 1 — SECRETS AND CREDENTIALS (HIGHEST PRIORITY)

### 5.1 When You Find a Hardcoded Secret

1. Do not commit the file with the secret still present. Never.
2. Report to the human immediately — they must rotate it before you make the replacement commit.
3. After rotation is confirmed, replace with Key Vault reference pattern (§5.2).
4. After the replacement PR is merged, clean git history using `git filter-repo` (NOT
   `git filter-branch` — deprecated).

### 5.2 Replacing Connection Strings with Key Vault References

**Before (dangerous — never leave in place):**
```json
{
  "ConnectionStrings": {
    "CosmosDb": "AccountEndpoint=https://account.documents.azure.com:443/;AccountKey=ACTUAL_KEY;"
  }
}
```

**Step 1 — Add Key Vault to configuration bootstrap:**
```csharp
// Program.cs
var kvName = builder.Configuration["KeyVaultName"]; // non-secret; safe in appsettings
if (!string.IsNullOrEmpty(kvName))
{
    var kvUri = new Uri($"https://{kvName}.vault.azure.net/");
    builder.Configuration.AddAzureKeyVault(
        kvUri, new DefaultAzureCredential(),
        new AzureKeyVaultConfigurationOptions { ReloadInterval = TimeSpan.FromMinutes(5) });
}
```

**Step 2 — Replace Cosmos DB connection string with Managed Identity:**
```csharp
// BEFORE (delete this)
var cosmosClient = new CosmosClient(configuration["ConnectionStrings:CosmosDb"]);
// AFTER
var credential = builder.Environment.IsDevelopment()
    ? new DefaultAzureCredential()
    : new ManagedIdentityCredential();
services.AddSingleton(_ => new CosmosClient(
    configuration["CosmosDb:Endpoint"], credential,
    new CosmosClientOptions { ConnectionMode = ConnectionMode.Direct }));
```

**Step 3 — Replace PostgreSQL connection string with Managed Identity token:**
```csharp
// BEFORE (delete this)
services.AddNpgsqlDataSource(configuration["ConnectionStrings:PostgreSQL"]);
// AFTER
var connStringWithoutPassword = configuration["PostgreSQL:ConnectionStringNoPassword"];
services.AddSingleton(_ =>
{
    var credential = builder.Environment.IsDevelopment()
        ? new DefaultAzureCredential()
        : new ManagedIdentityCredential();
    var dataSourceBuilder = new NpgsqlDataSourceBuilder(connStringWithoutPassword);
    dataSourceBuilder.UsePeriodicPasswordProvider(async (_, ct) =>
    {
        var token = await credential.GetTokenAsync(new TokenRequestContext(
            new[] { "https://ossrdbms-aad.database.windows.net/.default" }), ct);
        return token.Token;
    }, TimeSpan.FromHours(4), TimeSpan.FromSeconds(10));
    return dataSourceBuilder.Build();
});
```

### 5.3 .gitignore — Verify Completeness

```
.env
.env.*
!.env.example
appsettings.Development.json
appsettings.Production.json
appsettings.Staging.json
local.settings.json
launchSettings.json
*.pem
*.key
*.pfx
secrets/
.azure/
.aws/
.ssh/
```

---
