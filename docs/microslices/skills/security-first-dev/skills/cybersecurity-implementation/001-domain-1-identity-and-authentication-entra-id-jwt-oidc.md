---
id: skill-domain-1-identity-and-authentication-entra-id-jwt-oidc-0cdd0a0ea4
purpose: domain 1 identity and authentication entra id jwt oidc
source: src/vibey_tools/skills/plugins/security-first-dev/skills/cybersecurity-implementation/SKILL.md
requires: []
links: ["skill-domain-2-api-security-net-8-web-api-13c702198c"]
---

## DOMAIN 1: IDENTITY AND AUTHENTICATION (ENTRA ID, JWT, OIDC)

### Foundational — App Registrations and Correct Auth Flows

Create **separate Entra ID app registrations** for the API and each frontend (React SPA, Blazor
WASM). Use "Accounts in this organizational directory only" for single-tenant internal apps.

```bash
# Create API app registration
az ad app create --display-name "myapp-api" --sign-in-audience "AzureADMyOrg" \
  --identifier-uris "api://myapp-api"
# Create SPA app registration
az ad app create --display-name "myapp-spa" --sign-in-audience "AzureADMyOrg"
# Create service principal (Enterprise Application)
az ad sp create --id <APP_ID>
```

**Authentication flow selection is non-negotiable.** Wrong flows break security.

| Scenario | Required Flow | Never Use |
|---|---|---|
| React SPA user login | Authorization Code + PKCE | Implicit Grant (deprecated, disabled) |
| Blazor WASM user login | Authorization Code + PKCE | Implicit Grant |
| Service-to-service / daemons | Client Credentials | Shared secrets in config |
| API calling downstream API for user | On-Behalf-Of (OBO) | Storing user tokens in service |
| CLI tooling | Device Code | Embedded credentials |

**.NET 8 Web API — Microsoft.Identity.Web** (NuGet: `Microsoft.Identity.Web` v3.x/v4.x):

```csharp
// Program.cs
using Microsoft.Identity.Web;
builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddMicrosoftIdentityWebApi(builder.Configuration.GetSection("AzureAd"));
builder.Services.AddAuthorization();
```

```json
// appsettings.json — non-secret values only; ClientSecret must NEVER appear here
{
  "AzureAd": {
    "Instance": "https://login.microsoftonline.com/",
    "TenantId": "your-tenant-id",
    "ClientId": "your-api-client-id",
    "Audience": "api://your-api-client-id"
  }
}
```

**React with MSAL.js** (npm: `@azure/msal-browser` v3.x, `@azure/msal-react` v2.x):

```typescript
// authConfig.ts
export const msalConfig: Configuration = {
  auth: {
    clientId: "your-spa-client-id",
    authority: "https://login.microsoftonline.com/your-tenant-id",
    redirectUri: "/",
  },
  cache: {
    cacheLocation: "sessionStorage", // NEVER localStorage — XSS-vulnerable
    storeAuthStateInCookie: false,
  },
};
export const apiScopes = { scopes: ["api://your-api-client-id/Api.Read"] };
```

```tsx
// index.tsx — Instantiate OUTSIDE component tree (never inside a component)
const msalInstance = new PublicClientApplication(msalConfig);
await msalInstance.initialize();
await msalInstance.handleRedirectPromise();
const accounts = msalInstance.getAllAccounts();
if (accounts.length > 0) msalInstance.setActiveAccount(accounts[0]);
root.render(<MsalProvider instance={msalInstance}><App /></MsalProvider>);
```

**Blazor WASM** (NuGet: `Microsoft.Authentication.WebAssembly.Msal` v8.x):

```csharp
// Program.cs
builder.Services.AddMsalAuthentication(options =>
{
    builder.Configuration.Bind("AzureAd", options.ProviderOptions.Authentication);
    options.ProviderOptions.DefaultAccessTokenScopes.Add(
        "api://your-api-client-id/Api.Read");
    options.ProviderOptions.LoginMode = "redirect";
});
```

**Critical anti-patterns to avoid:**
- Storing tokens in `localStorage` (XSS-vulnerable)
- Enabling implicit grant checkboxes in app registration
- Sharing a single app registration across environments
- Hardcoding client secrets in source code
- Creating `PublicClientApplication` inside React components (re-created on every render)

### Intermediate — JWT Validation, App Roles, Token Lifecycle

JWT validation in .NET must enforce issuer, audience, lifetime, and signing key — all handled
automatically by `AddMicrosoftIdentityWebApi`. If configuring manually: `ClockSkew = TimeSpan.Zero`
(the 5-minute default is too generous). Never hardcode signing keys — Microsoft rotates them via
the JWKS endpoint.

**App Roles in manifest:**
```json
{
  "appRoles": [
    {
      "allowedMemberTypes": ["User"],
      "displayName": "Admin",
      "id": "unique-guid-here",
      "isEnabled": true,
      "value": "Admin"
    }
  ]
}
```

**Map App Roles to authorization policies:**
```csharp
builder.Services.AddAuthorizationBuilder()
    .AddPolicy("AdminOnly", policy => policy.RequireRole("Admin"))
    .AddPolicy("ReaderOrAdmin", policy => policy.RequireRole("Reader", "Admin"))
    .AddPolicy("DepartmentFinance", policy =>
        policy.RequireClaim("department", "finance"));
```

**Use App Roles over Group Claims.** Groups create an overage problem: users with more than 200
groups cause Entra ID to emit a `_claim_sources` reference instead of the groups array, requiring
a Graph API call. App Roles are portable and don't have this limitation.

**Token storage in SPAs:** MSAL.js keeps tokens in-memory by default. `sessionStorage` is the
most secure persistent option (per-tab isolation, auto-clears on tab close). **Refresh token
rotation is automatic** — SPAs receive one-time-use refresh tokens that rotate on each use.
Replaying a used token revokes the entire token family.

### Advanced — Managed Identities, Conditional Access, Zero-Secrets

**Managed Identities eliminate all secrets from your .NET API configuration.** Core NuGet:
`Azure.Identity` (v1.13.x).

```csharp
// Production-optimized credential selection
var credential = builder.Environment.IsDevelopment()
    ? new DefaultAzureCredential()
    : new ManagedIdentityCredential();  // Faster startup — skips environment probing

// CosmosDB with Managed Identity
var cosmosClient = new CosmosClient("https://your-account.documents.azure.com:443/", credential);

// PostgreSQL with periodic token refresh (tokens expire in 4-24 hours)
var dataSourceBuilder = new NpgsqlDataSourceBuilder(connStringWithoutPassword);
dataSourceBuilder.UsePeriodicPasswordProvider(async (_, ct) =>
{
    var token = await credential.GetTokenAsync(new TokenRequestContext(
        new[] { "https://ossrdbms-aad.database.windows.net/.default" }), ct);
    return token.Token;
}, TimeSpan.FromHours(4), TimeSpan.FromSeconds(10));
```

```bash
# Assign Cosmos DB Built-in Data Contributor role
az cosmosdb sql role assignment create \
  --account-name myCosmosAccount --resource-group myRG \
  --role-definition-id "00000000-0000-0000-0000-000000000002" \
  --principal-id "<managed-identity-object-id>" --scope "/"
```

**Conditional Access policies to deploy:**
1. Require MFA for all users (exclude break-glass accounts)
2. Block legacy authentication protocols (SMTP, IMAP, POP3 bypass Conditional Access)
3. Require compliant devices via Intune
4. Require MFA from non-trusted network locations

Always test with Report-only mode and the What If tool before enforcement.

---
