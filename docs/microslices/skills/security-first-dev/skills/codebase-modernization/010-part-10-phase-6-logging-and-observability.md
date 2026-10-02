---
id: skill-part-10-phase-6-logging-and-observability-563c95eaba
purpose: part 10 phase 6 logging and observability
source: src/vibey_tools/skills/plugins/security-first-dev/skills/codebase-modernization/SKILL.md
requires: ["skill-part-9-phase-5-test-coverage-and-security-tests-dfa732e247"]
links: ["skill-part-11-phase-7-devsecops-pipeline-installation-270a561894"]
---

## PART 10: PHASE 6 — LOGGING AND OBSERVABILITY

### 10.1 Migrating from Console.WriteLine to Structured Logging

```csharp
// BEFORE: unstructured, not searchable
Console.WriteLine($"Processing order {orderId} for user {userId}");
// AFTER: structured, searchable in Application Insights
_logger.LogInformation("Processing order {OrderId} for {UserId}", orderId, userId);
```

### 10.2 Adding Correlation ID Propagation

```csharp
public class CorrelationIdMiddleware
{
    private const string HeaderName = "x-correlation-id";
    public async Task InvokeAsync(HttpContext context)
    {
        var correlationId = context.Request.Headers[HeaderName].FirstOrDefault()
            ?? Guid.NewGuid().ToString("N");
        context.Response.Headers[HeaderName] = correlationId;
        using var scope = _logger.BeginScope(
            new Dictionary<string, object> { ["CorrelationId"] = correlationId });
        context.TraceIdentifier = correlationId;
        await _next(context);
    }
}
app.UseMiddleware<CorrelationIdMiddleware>(); // before UseRouting
```

### 10.3 Removing PII from Existing Logs

```bash
grep -rn "_logger\.\|Log\.\|Console\." src/ --include="*.cs" | \
  grep -i "email\|password\|token\|ssn\|credit\|phone\|address"
```

Replace actual values with anonymized identifiers:
```csharp
// BEFORE — logs actual email address
_logger.LogInformation("User {Email} logged in", user.Email);
// AFTER — logs only anonymized ID
_logger.LogInformation("User {UserId} logged in", user.Id);
```

---
