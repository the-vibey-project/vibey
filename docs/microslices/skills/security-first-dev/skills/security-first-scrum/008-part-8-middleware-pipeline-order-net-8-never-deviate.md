---
id: skill-part-8-middleware-pipeline-order-net-8-never-deviate-4c83a526e5
purpose: part 8 middleware pipeline order net 8 never deviate
source: src/vibey_tools/skills/plugins/security-first-dev/skills/security-first-scrum/SKILL.md
requires: ["skill-part-7-tdd-the-only-acceptable-workflow-6b511246bb"]
links: ["skill-part-9-identity-authentication-and-authorization-5295d6273f"]
---

## PART 8: MIDDLEWARE PIPELINE ORDER (.NET 8) — NEVER DEVIATE

```csharp
var app = builder.Build();

if (app.Environment.IsDevelopment()) { app.UseSwagger(); app.UseSwaggerUI(); }
else { app.UseHsts(); }

// Security headers — must be first substantial middleware
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
app.UseRateLimiter();        // Rate limit before auth to block brute force
app.UseCors("SpaPolicy");
app.UseAuthentication();    // WHO are you?
app.UseAuthorization();     // WHAT can you do?
app.MapControllers();
```

Remove Kestrel Server header: `builder.WebHost.ConfigureKestrel(o => o.AddServerHeader = false);`

**`UseAuthentication` must precede `UseAuthorization`. Reversing them causes authentication to
silently fail and authorization to pass for all requests, including unauthenticated ones.**

---
