---
id: skill-part-6-phase-2-authentication-and-authorization-migration-f452bf3ae5
purpose: part 6 phase 2 authentication and authorization migration
source: src/vibey_tools/skills/plugins/security-first-dev/skills/codebase-modernization/SKILL.md
requires: ["skill-part-5-phase-1-secrets-and-credentials-highest-priority-d9b8adb68c"]
links: ["skill-part-7-phase-3-input-validation-and-query-safety-4b129cda19"]
---

## PART 6: PHASE 2 — AUTHENTICATION AND AUTHORIZATION MIGRATION

### 6.1 Find Unprotected Controllers

```bash
grep -rn "public class.*Controller" src/ --include="*.cs" -l | while read f; do
  if ! grep -q "\[Authorize" "$f"; then
    echo "No [Authorize] found: $f"
  fi
done
grep -rn "\[AllowAnonymous\]" src/ --include="*.cs"  # each needs a documented reason
```

### 6.2 Migrating to Microsoft.Identity.Web

**Before (legacy JWT):**
```csharp
services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options => {
        options.TokenValidationParameters = new TokenValidationParameters {
            ValidIssuer = "https://sts.windows.net/YOUR-TENANT/",
            ValidAudience = "api://YOUR-APP-ID",
            // Common legacy mistake: ClockSkew left at default 5 minutes
        };
    });
```

**After (Microsoft.Identity.Web):**
```csharp
builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddMicrosoftIdentityWebApi(builder.Configuration.GetSection("AzureAd"));
builder.Services.AddAuthorizationBuilder()
    .AddPolicy("AdminOnly",     p => p.RequireRole("Admin"))
    .AddPolicy("ReaderOrAdmin", p => p.RequireRole("Reader", "Admin"))
    .AddPolicy("WriterOrAdmin", p => p.RequireRole("Writer", "Admin"));
```

Required packages:
```bash
dotnet add package Microsoft.Identity.Web
dotnet add package Azure.Identity
# Remove any hand-rolled JWT validation packages
```

### 6.3 Adding [Authorize] — Controller by Controller

Do this controller-by-controller, not as a mass change. Each controller = its own PR:

```csharp
[ApiController]
[Route("api/v1/[controller]")]
[Authorize]  // minimum: authenticated caller required
public class DocumentsController : ControllerBase { }

[HttpGet("{id}")]
[Authorize(Policy = "ReaderOrAdmin")]
public async Task<ActionResult<DocumentResponse>> GetByIdAsync(string id, CancellationToken ct) { }

[HttpGet("health")]
[AllowAnonymous] // REASON: Public health check — no data returned
public IActionResult Health() => Ok("healthy");
```

### 6.4 Adding BOLA Protection to Existing Endpoints

BOLA is the most common API vulnerability and is usually completely absent. Add it to the
service layer — not the controller:

```csharp
// BEFORE: No ownership check
public async Task<DocumentModel> GetDocumentAsync(string documentId, CancellationToken ct)
{
    return await _repository.FindByIdAsync(documentId, ct);
}

// AFTER: Ownership enforced before data is returned
public async Task<DocumentModel> GetDocumentAsync(
    string documentId, string requestingUserId, CancellationToken ct)
{
    var document = await _repository.FindByIdAsync(documentId, ct);
    if (document.OwnerId != requestingUserId)
        throw new ResourceOwnershipException(
            $"User {requestingUserId} does not own document {documentId}");
    return document;
}
```

Controller side — extract userId from JWT:
```csharp
var userId = User.GetObjectId()  // Microsoft.Identity.Web extension method
    ?? throw new UnauthorizedAccessException("UserId claim missing from token");
var document = await _documentService.GetDocumentAsync(id, userId, ct);
```

### 6.5 Migrating React from localStorage to sessionStorage

```typescript
// BEFORE — delete this
cache: { cacheLocation: "localStorage" }
// AFTER
cache: { cacheLocation: "sessionStorage", storeAuthStateInCookie: false }
```

### 6.6 Migrating from Implicit Grant to Authorization Code + PKCE

**What you do (code):** Verify MSAL.js v3 is installed.
```bash
npm install @azure/msal-browser@latest @azure/msal-react@latest
```

**What the human does (Azure portal):**
- App registration → Authentication → Remove checkboxes for "Access tokens" and "ID tokens"
  under Implicit grant.
- Verify redirect URIs are correct.

### 6.7 Middleware Pipeline Order — Fix If Wrong

This is the single most common .NET security misconfiguration:

```csharp
// CORRECT ORDER
app.UseHsts();
app.UseHttpsRedirection();
app.UseSerilogRequestLogging();
app.UseRouting();
app.UseRateLimiter();
app.UseCors("SpaPolicy");
app.UseAuthentication();  // WHO are you? — MUST come before UseAuthorization
app.UseAuthorization();   // WHAT can you do?
app.MapControllers();
```

If `UseAuthorization` appears before `UseAuthentication` in existing code: this is a P0 finding.
The middleware silently treats all requests as unauthenticated. Fix immediately.

---
