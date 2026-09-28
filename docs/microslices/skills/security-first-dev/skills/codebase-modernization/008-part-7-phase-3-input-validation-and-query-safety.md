---
id: skill-part-7-phase-3-input-validation-and-query-safety-4b129cda19
purpose: part 7 phase 3 input validation and query safety
source: src/vibey_tools/skills/plugins/security-first-dev/skills/codebase-modernization/SKILL.md
requires: ["skill-part-6-phase-2-authentication-and-authorization-migration-f452bf3ae5"]
links: ["skill-part-8-phase-4-architecture-refactoring-p3-priority-a0edb5dc21"]
---

## PART 7: PHASE 3 — INPUT VALIDATION AND QUERY SAFETY

### 7.1 Replacing String-Interpolated SQL Queries

**.NET / Npgsql:**
```csharp
// BEFORE — SQL injection vulnerable
var users = await _conn.QueryAsync<User>(
    $"SELECT * FROM users WHERE email = '{email}' AND tenant_id = '{tenantId}'");
// AFTER — parameterized
var users = await _conn.QueryAsync<User>(
    "SELECT * FROM users WHERE email = @email AND tenant_id = @tenantId",
    new { email, tenantId });
```

**.NET / Cosmos DB:**
```csharp
// BEFORE — string interpolation in Cosmos query
var query = new QueryDefinition(
    $"SELECT * FROM c WHERE c.userId = '{userId}' AND c.type = '{docType}'");
// AFTER — parameterized
var query = new QueryDefinition(
    "SELECT * FROM c WHERE c.userId = @userId AND c.type = @docType")
    .WithParameter("@userId", userId)
    .WithParameter("@docType", docType);
```

**EF Core:**
```csharp
// BEFORE — vulnerable
var results = _context.Users.FromSqlRaw($"SELECT * FROM Users WHERE Id = {userId}");
// AFTER — prefer LINQ (EF generates safe SQL)
var results = _context.Users.Where(u => u.Id == userId);
```

### 7.2 Adding FluentValidation

```bash
dotnet add package FluentValidation
dotnet add package FluentValidation.DependencyInjectionExtensions
# Do NOT install FluentValidation.AspNetCore — it is deprecated
```

```csharp
public class CreateUserRequestValidator : AbstractValidator<CreateUserRequest>
{
    public CreateUserRequestValidator()
    {
        RuleFor(x => x.Name).NotEmpty().MaximumLength(100)
            .Matches(@"^[\w\s\-'\.]+$").WithMessage("Name contains invalid characters.");
        RuleFor(x => x.Email).NotEmpty().EmailAddress().MaximumLength(254);
    }
}
builder.Services.AddValidatorsFromAssemblyContaining<CreateUserRequestValidator>();
```

### 7.3 Fixing dangerouslySetInnerHTML

```bash
grep -rn "dangerouslySetInnerHTML" src/ --include="*.tsx" --include="*.jsx"
```

For each hit with user-controlled content:
```tsx
// BEFORE — XSS vulnerability
<div dangerouslySetInnerHTML={{ __html: userProfile.bio }} />
// AFTER — DOMPurify sanitization
import DOMPurify from 'dompurify';
<div dangerouslySetInnerHTML={{
  __html: DOMPurify.sanitize(userProfile.bio, {
    ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'a'],
    FORBID_TAGS: ['script', 'style', 'iframe'],
    FORBID_ATTR: ['onerror', 'onload', 'onclick'],
  })
}} />
```

### 7.4 Tightening CORS

```csharp
// BEFORE — never acceptable in production
app.UseCors(builder => builder.AllowAnyOrigin().AllowAnyMethod().AllowAnyHeader());
// AFTER — exact allowed origins from configuration
var allowedOrigins = builder.Configuration
    .GetSection("Cors:AllowedOrigins").Get<string[]>()
    ?? throw new InvalidOperationException("Cors:AllowedOrigins must be configured");
builder.Services.AddCors(options =>
{
    options.AddPolicy("SpaPolicy", policy => policy
        .WithOrigins(allowedOrigins)
        .AllowAnyHeader().AllowAnyMethod().AllowCredentials());
});
```

### 7.5 Adding Rate Limiting

```csharp
builder.Services.AddRateLimiter(options =>
{
    options.RejectionStatusCode = StatusCodes.Status429TooManyRequests;
    options.GlobalLimiter = PartitionedRateLimiter.Create<HttpContext, string>(
        httpContext => RateLimitPartition.GetFixedWindowLimiter(
            partitionKey: httpContext.User.Identity?.Name
                ?? httpContext.Connection.RemoteIpAddress?.ToString() ?? "anon",
            factory: _ => new FixedWindowRateLimiterOptions
            {
                PermitLimit = 60, Window = TimeSpan.FromMinutes(1), QueueLimit = 0,
            }));
});
// In middleware pipeline — MUST be after UseRouting, before UseAuthentication
app.UseRateLimiter();
```

---
