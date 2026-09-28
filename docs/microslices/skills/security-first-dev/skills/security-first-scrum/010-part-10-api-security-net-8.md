---
id: skill-part-10-api-security-net-8-39282394b9
purpose: part 10 api security net 8
source: src/vibey_tools/skills/plugins/security-first-dev/skills/security-first-scrum/SKILL.md
requires: ["skill-part-9-identity-authentication-and-authorization-5295d6273f"]
links: ["skill-part-11-frontend-security-3693f41d54"]
---

## PART 10: API SECURITY (.NET 8)

### Rate Limiting

```csharp
builder.Services.AddRateLimiter(options =>
{
    options.RejectionStatusCode = StatusCodes.Status429TooManyRequests;
    options.AddTokenBucketLimiter("Api", opt =>
    {
        opt.TokenLimit = 100;
        opt.ReplenishmentPeriod = TimeSpan.FromSeconds(10);
        opt.TokensPerPeriod = 20;
        opt.QueueLimit = 5;
    });
    // Per-user rate limiting (falls back to IP for anonymous)
    options.GlobalLimiter = PartitionedRateLimiter.Create<HttpContext, string>(
        httpContext => RateLimitPartition.GetFixedWindowLimiter(
            partitionKey: httpContext.User.Identity?.Name
                ?? httpContext.Connection.RemoteIpAddress?.ToString() ?? "anon",
            factory: _ => new FixedWindowRateLimiterOptions
            {
                PermitLimit = 60, Window = TimeSpan.FromMinutes(1)
            }));
});
```

### Input Validation with FluentValidation

```csharp
public class CreateUserRequestValidator : AbstractValidator<CreateUserRequest>
{
    public CreateUserRequestValidator()
    {
        RuleFor(x => x.Name).NotEmpty().MaximumLength(100)
            .Matches(@"^[a-zA-Z\s\-']+$").WithMessage("Name contains invalid characters.");
        RuleFor(x => x.Email).NotEmpty().EmailAddress();
        RuleFor(x => x.Age).InclusiveBetween(18, 120);
    }
}
// Program.cs — use base package, not the deprecated .AspNetCore package
builder.Services.AddValidatorsFromAssemblyContaining<CreateUserRequestValidator>();
```

### CORS — Exact Origins Only

```csharp
var allowedOrigins = builder.Configuration
    .GetSection("Cors:AllowedOrigins").Get<string[]>()!;
builder.Services.AddCors(options =>
{
    options.AddPolicy("SpaPolicy", policy => policy
        .WithOrigins(allowedOrigins)  // NEVER AllowAnyOrigin() in production
        .AllowAnyHeader().AllowAnyMethod().AllowCredentials());
});
```

Note: trailing slash in origin URLs causes silent comparison failure — omit it.

### Key Vault Bootstrap

```csharp
var kvUri = new Uri($"https://{builder.Configuration["KeyVaultName"]}.vault.azure.net/");
builder.Configuration.AddAzureKeyVault(kvUri, new DefaultAzureCredential(),
    new AzureKeyVaultConfigurationOptions { ReloadInterval = TimeSpan.FromMinutes(5) });
```

---
