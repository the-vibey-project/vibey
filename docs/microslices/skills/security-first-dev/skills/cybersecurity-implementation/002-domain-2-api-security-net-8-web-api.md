---
id: skill-domain-2-api-security-net-8-web-api-13c702198c
purpose: domain 2 api security net 8 web api
source: src/vibey_tools/skills/plugins/security-first-dev/skills/cybersecurity-implementation/SKILL.md
requires: ["skill-domain-1-identity-and-authentication-entra-id-jwt-oidc-0cdd0a0ea4"]
links: ["skill-domain-3-frontend-security-react-and-blazor-wasm-f10ec2aa95"]
---

## DOMAIN 2: API SECURITY (.NET 8 WEB API)

### Foundational — Middleware Pipeline ORDER (Critical), Validation, CORS

**Middleware ordering is the single most common security misconfiguration in .NET APIs.**
`UseAuthentication` must precede `UseAuthorization` — reversing them causes authentication to
silently fail and authorization to pass for all requests.

```csharp
var app = builder.Build();

if (app.Environment.IsDevelopment()) { app.UseSwagger(); app.UseSwaggerUI(); }
else { app.UseHsts(); }

// Security headers — first substantial middleware
app.Use(async (context, next) => {
    context.Response.Headers["X-Content-Type-Options"] = "nosniff";
    context.Response.Headers["X-Frame-Options"] = "DENY";
    context.Response.Headers["Referrer-Policy"] = "strict-origin-when-cross-origin";
    context.Response.Headers["Permissions-Policy"] =
        "accelerometer=(), camera=(), geolocation=(), microphone=()";
    await next();
});

app.UseHttpsRedirection();
app.UseSerilogRequestLogging();
app.UseRouting();
app.UseRateLimiter();        // Rate limit BEFORE auth to block brute force
app.UseCors("SpaPolicy");
app.UseAuthentication();    // WHO are you?
app.UseAuthorization();     // WHAT can you do?
app.MapControllers();
```

Remove Kestrel Server header: `builder.WebHost.ConfigureKestrel(o => o.AddServerHeader = false);`

**Input validation** with FluentValidation (NuGet: `FluentValidation` v11.x +
`FluentValidation.DependencyInjectionExtensions`). Note: `FluentValidation.AspNetCore` is
deprecated — use the base package:

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
// Program.cs
builder.Services.AddValidatorsFromAssemblyContaining<CreateUserRequestValidator>();
```

**CORS — exact allowed origins only:**
```csharp
var allowedOrigins = builder.Configuration.GetSection("Cors:AllowedOrigins").Get<string[]>()!;
builder.Services.AddCors(options =>
{
    options.AddPolicy("SpaPolicy", policy => policy
        .WithOrigins(allowedOrigins)  // NEVER AllowAnyOrigin() in production
        .AllowAnyHeader().AllowAnyMethod().AllowCredentials());
});
```

Trailing slash in origin URLs (`"https://app.example.com/"`) causes silent comparison failure.
Omit trailing slashes.

### Intermediate — Rate Limiting, BOLA via IAuthorizationHandler, Logging

**Built-in rate limiting in .NET 8** (no extra NuGet needed):

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
    // Per-user rate limiting (falls back to IP for unauthenticated)
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

Apply with `[EnableRateLimiting("Api")]` on controllers or `.RequireRateLimiting("Api")` on
minimal API routes.

**BOLA prevention via IAuthorizationHandler** (OWASP API1 — Broken Object Level Authorization):

```csharp
public class DocumentAuthorizationHandler
    : AuthorizationHandler<SameAuthorRequirement, Document>
{
    protected override Task HandleRequirementAsync(
        AuthorizationHandlerContext context,
        SameAuthorRequirement requirement, Document resource)
    {
        if (context.User.Identity?.Name == resource.AuthorId)
            context.Succeed(requirement);
        // Never call context.Succeed for unauthorized access — implicit failure is correct
        return Task.CompletedTask;
    }
}
```

**Serilog with Application Insights:**
```csharp
builder.Host.UseSerilog((context, services, config) => config
    .ReadFrom.Configuration(context.Configuration)
    .Enrich.FromLogContext()
    .WriteTo.Console()
    .WriteTo.ApplicationInsights(
        services.GetRequiredService<TelemetryConfiguration>(),
        TelemetryConverter.Traces));
```

Never log passwords, JWTs, API keys, connection strings, credit card numbers, or PII. Always log
failed auth, authorization denials, and suspicious input with structured fields.

### Advanced — Key Vault Config, Swagger Lockdown, Minimal API Security

**Zero-secrets configuration with Azure Key Vault:**
```csharp
var kvUri = new Uri($"https://{builder.Configuration["KeyVaultName"]}.vault.azure.net/");
builder.Configuration.AddAzureKeyVault(kvUri, new DefaultAzureCredential(),
    new AzureKeyVaultConfigurationOptions { ReloadInterval = TimeSpan.FromMinutes(5) });
```

Secrets auto-refresh without restarts when using `IOptionsMonitor<T>`.

**Swagger must never be exposed in production:**
```csharp
if (app.Environment.IsDevelopment()) { app.UseSwagger(); app.UseSwaggerUI(); }
// For Swagger JWT auth in development — use Http type, not ApiKey
options.AddSecurityDefinition("Bearer", new OpenApiSecurityScheme
{
    Type = SecuritySchemeType.Http,
    Scheme = "Bearer",
    BearerFormat = "JWT"
});
```

**Minimal APIs — route group authorization:**
```csharp
var admin = app.MapGroup("/api/admin").RequireAuthorization("AdminOnly");
admin.MapGet("/users", () => Results.Ok());
admin.MapDelete("/users/{id}", (int id) => Results.NoContent());
// Explicit anonymous — document why
app.MapGet("/api/health", () => Results.Ok("healthy")).AllowAnonymous();
```

---
