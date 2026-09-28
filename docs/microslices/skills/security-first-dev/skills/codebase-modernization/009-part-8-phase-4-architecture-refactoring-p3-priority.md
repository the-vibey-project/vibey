---
id: skill-part-8-phase-4-architecture-refactoring-p3-priority-a0edb5dc21
purpose: part 8 phase 4 architecture refactoring p3 priority
source: src/vibey_tools/skills/plugins/security-first-dev/skills/codebase-modernization/SKILL.md
requires: ["skill-part-7-phase-3-input-validation-and-query-safety-4b129cda19"]
links: ["skill-part-9-phase-5-test-coverage-and-security-tests-b1cf602c1b"]
---

## PART 8: PHASE 4 — ARCHITECTURE REFACTORING (P3 PRIORITY)

**Do not start Phase 4 if P0–P2 work is outstanding. Architecture refactoring carries the most
risk of regressions. Every change must be covered by tests before and after.**

### 8.1 Extracting Business Logic from Controllers

Use the extract → interface → test → delete approach (never all at once):

```csharp
// BEFORE: Controller doing direct DB work and business logic
[HttpPost]
public async Task<IActionResult> CreateOrder(CreateOrderRequest request)
{
    if (request.Quantity > 100) return BadRequest("Quantity exceeds limit");  // business logic
    var order = new Order { ... };
    await _dbContext.Orders.AddAsync(order);   // direct DB — wrong layer
    await _dbContext.SaveChangesAsync();
    return CreatedAtAction(...);
}

// AFTER STEP 1: Interface first
public interface IOrderService
{
    Task<OrderModel> CreateOrderAsync(
        CreateOrderRequest request, string requestingUserId, CancellationToken ct);
}

// AFTER STEP 2: Implement the service (write test first)
public class OrderService : IOrderService
{
    private readonly IOrderRepository _repository;
    public async Task<OrderModel> CreateOrderAsync(
        CreateOrderRequest request, string requestingUserId, CancellationToken ct)
    {
        if (request.Quantity > 100)
            throw new ValidationException("Quantity exceeds the maximum of 100.");
        var order = new Order { OwnerId = requestingUserId, ... };
        return await _repository.SaveAsync(order, ct);
    }
}

// AFTER STEP 3: Controller becomes thin
[HttpPost]
[Authorize(Policy = "WriterOrAdmin")]
public async Task<ActionResult<OrderResponse>> CreateAsync(
    CreateOrderRequest request, CancellationToken ct)
{
    var userId = User.GetObjectId()
        ?? throw new UnauthorizedAccessException("UserId missing from token");
    var order = await _orderService.CreateOrderAsync(request, userId, ct);
    return CreatedAtAction(nameof(GetByIdAsync), new { id = order.Id },
        _mapper.Map<OrderResponse>(order));
}
```

### 8.2 Extracting Repositories from Services

```csharp
// Interface in Infrastructure/Repositories/Interfaces/
public interface IOrderRepository
{
    Task<OrderModel> FindByIdAsync(string id, CancellationToken ct);
    Task<OrderModel> SaveAsync(OrderModel order, CancellationToken ct);
    Task DeleteAsync(string id, CancellationToken ct);
}

// Fake for unit tests (in Mocks/)
public class FakeOrderRepository : IOrderRepository
{
    private readonly Dictionary<string, OrderModel> _store = new();
    public Task<OrderModel> FindByIdAsync(string id, CancellationToken ct)
    {
        if (!_store.TryGetValue(id, out var order))
            throw new NotFoundException($"Order {id} not found.");
        return Task.FromResult(order);
    }
    public Task<OrderModel> SaveAsync(OrderModel order, CancellationToken ct)
    {
        _store[order.Id] = order; return Task.FromResult(order);
    }
    public Task DeleteAsync(string id, CancellationToken ct)
    {
        if (!_store.Remove(id)) throw new NotFoundException($"Order {id} not found.");
        return Task.CompletedTask;
    }
    public IReadOnlyList<OrderModel> GetAll() => _store.Values.ToList();
    public int Count => _store.Count;
    public void Clear() => _store.Clear();
}
```

### 8.3 Typed Exception Hierarchy

```csharp
// Domain layer
public abstract class AppException : Exception { ... }
public sealed class ValidationException : AppException { ... }
public sealed class NotFoundException : AppException { ... }
public sealed class AuthException : AppException { ... }          // never retry
public sealed class ResourceOwnershipException : AppException { ... } // never retry
public sealed class TransientException : AppException { ... }    // retry with backoff

// Global exception handler — maps to RFC 7807 ProblemDetails
public class GlobalExceptionHandler : IExceptionHandler
{
    public async ValueTask<bool> TryHandleAsync(HttpContext ctx, Exception ex, CancellationToken ct)
    {
        var (statusCode, title) = ex switch
        {
            ValidationException         => (400, "Validation failed"),
            NotFoundException           => (404, "Resource not found"),
            AuthException               => (401, "Authentication required"),
            ResourceOwnershipException  => (403, "Access denied"),
            TransientException          => (503, "Service temporarily unavailable"),
            _                           => (500, "An unexpected error occurred"),
        };
        // Never leak internal details to clients
        var problem = new ProblemDetails
        {
            Status = statusCode, Title = title,
            Extensions = { ["correlationId"] = ctx.TraceIdentifier }
        };
        _logger.LogError(ex, "Request failed: {StatusCode} {Title} (CorrelationId: {CorrelationId})",
            statusCode, title, ctx.TraceIdentifier);
        ctx.Response.StatusCode = statusCode;
        await ctx.Response.WriteAsJsonAsync(problem, ct);
        return true;
    }
}
```

---
