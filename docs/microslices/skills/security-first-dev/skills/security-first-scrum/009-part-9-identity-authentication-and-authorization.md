---
id: skill-part-9-identity-authentication-and-authorization-5295d6273f
purpose: part 9 identity authentication and authorization
source: src/vibey_tools/skills/plugins/security-first-dev/skills/security-first-scrum/SKILL.md
requires: ["skill-part-8-middleware-pipeline-order-net-8-never-deviate-4c83a526e5"]
links: ["skill-part-10-api-security-net-8-39282394b9"]
---

## PART 9: IDENTITY, AUTHENTICATION, AND AUTHORIZATION

### Authentication Flow Selection (Non-Negotiable)

| Scenario | Required Flow | Never Use |
|---|---|---|
| React SPA user login | Authorization Code + PKCE | Implicit Grant (deprecated) |
| Blazor WASM user login | Authorization Code + PKCE | Implicit Grant (deprecated) |
| Service-to-service | Client Credentials | Shared secrets in config |
| API calling downstream API for user | On-Behalf-Of (OBO) | Storing user tokens in service |
| CLI tooling | Device Code | Embedded credentials |

### .NET 8 — Microsoft.Identity.Web Setup

```csharp
// Program.cs
builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddMicrosoftIdentityWebApi(builder.Configuration.GetSection("AzureAd"));
builder.Services.AddAuthorization();
```

JWT validation rules: `ClockSkew = TimeSpan.Zero`. Never hardcode signing keys.
Always validate: issuer, audience, lifetime, and signing key.

### RBAC — App Roles (Prefer Over Group Claims)

```csharp
builder.Services.AddAuthorizationBuilder()
    .AddPolicy("AdminOnly", policy => policy.RequireRole("Admin"))
    .AddPolicy("ReaderOrAdmin", policy => policy.RequireRole("Reader", "Admin"))
    .AddPolicy("DepartmentFinance", policy =>
        policy.RequireClaim("department", "finance"));
```

Use App Roles, not Group Claims. Groups create a 200-group overage problem requiring Graph API
calls. App Roles are portable and have no overage.

### BOLA Prevention (OWASP API1)

Resource-level authorization lives in the **service layer**, not the controller:

```csharp
// IAuthorizationHandler implementation for resource-level checks
public class DocumentAuthorizationHandler
    : AuthorizationHandler<SameAuthorRequirement, Document>
{
    protected override Task HandleRequirementAsync(
        AuthorizationHandlerContext context,
        SameAuthorRequirement requirement, Document resource)
    {
        if (context.User.Identity?.Name == resource.AuthorId)
            context.Succeed(requirement);
        // Never call context.Succeed for unauthorized access
        return Task.CompletedTask;
    }
}
```

Every endpoint that returns user-owned data must have a resource-level authorization check.
Never rely on "the user can only see their own ID in the UI."

### Managed Identity — Zero-Secrets Pattern

```csharp
// Credential selection — never use connection strings with keys
var credential = builder.Environment.IsDevelopment()
    ? new DefaultAzureCredential()
    : new ManagedIdentityCredential();  // Faster startup in production

// Cosmos DB with Managed Identity
var cosmosClient = new CosmosClient(
    "https://your-account.documents.azure.com:443/",
    credential,
    new CosmosClientOptions { ConnectionMode = ConnectionMode.Direct });

// PostgreSQL with Managed Identity (token rotation every 4 hours)
var dataSourceBuilder = new NpgsqlDataSourceBuilder(connStringWithoutPassword);
dataSourceBuilder.UsePeriodicPasswordProvider(async (_, ct) =>
{
    var token = await credential.GetTokenAsync(
        new TokenRequestContext(
            new[] { "https://ossrdbms-aad.database.windows.net/.default" }), ct);
    return token.Token;
}, TimeSpan.FromHours(4), TimeSpan.FromSeconds(10));
```

### React MSAL.js

```typescript
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

// Axios interceptor for automatic token injection
apiClient.interceptors.request.use(async (config) => {
  const account = msalInstance.getActiveAccount();
  if (!account) throw new Error('No active account');
  try {
    const response = await msalInstance.acquireTokenSilent({
      scopes: ['api://your-api-client-id/.default'], account,
    });
    config.headers.Authorization = `Bearer ${response.accessToken}`;
  } catch (error) {
    if (error instanceof InteractionRequiredAuthError) {
      await msalInstance.acquireTokenRedirect({
        scopes: ['api://your-api-client-id/.default'],
      });
    }
  }
  return config;
});
```

Instantiate `PublicClientApplication` OUTSIDE the component tree — never inside a component.

### Blazor WASM

```csharp
builder.Services.AddMsalAuthentication(options =>
{
    builder.Configuration.Bind("AzureAd", options.ProviderOptions.Authentication);
    options.ProviderOptions.DefaultAccessTokenScopes.Add(
        "api://your-api-client-id/Api.Read");
    options.ProviderOptions.LoginMode = "redirect";
});
```

**Critical:** Blazor WASM assemblies are downloadable and decompilable. All `[Authorize]` and
`AuthorizeView` components are UX features only. The API must re-validate every request. Never
put secrets, sensitive business logic, or IP in WASM code.

---
