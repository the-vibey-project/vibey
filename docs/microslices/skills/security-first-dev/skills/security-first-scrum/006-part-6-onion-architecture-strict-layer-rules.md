---
id: skill-part-6-onion-architecture-strict-layer-rules-d550544859
purpose: part 6 onion architecture strict layer rules
source: src/vibey_tools/skills/plugins/security-first-dev/skills/security-first-scrum/SKILL.md
requires: ["skill-part-5-project-anatomy-c6ec05eefa"]
links: ["skill-part-7-tdd-the-only-acceptable-workflow-6b511246bb"]
---

## PART 6: ONION ARCHITECTURE — STRICT LAYER RULES

```
+----------------------------------------------------------+
|  Entry Points (Controllers / Adapters)                   |  <- outermost; validates auth + input
|  +----------------------------------------------------+  |
|  |  Services (Use Cases / Workflows)                  |  |  <- business logic; no I/O
|  |  +----------------------------------------------+ |  |
|  |  |  Domain (Models / Contracts / Exceptions)    | |  |  <- innermost; zero dependencies
|  |  +----------------------------------------------+ |  |
|  |  Repositories (Ports / Adapters)                  |  |  <- all I/O here; Managed Identity
|  +----------------------------------------------------+  |
|  Infrastructure (Config / Key Vault / Logging / DI)      |  <- wires everything; no logic
+----------------------------------------------------------+
```

**Dependency rule: dependencies point inward only.**

- Domain has zero external dependencies (no framework, no I/O, no Azure SDKs, no EF Core).
- Services know domain and repository *interfaces*, never concrete implementations.
- Controllers implement a controller *interface* and know service *interfaces* only.
- Infrastructure wires everything via DI.

### Security Responsibilities by Layer

**Controllers / Entry Points:**
- Every endpoint decorated with `[Authorize(Policy = "...")]` or explicitly `[AllowAnonymous]`.
  No endpoint is auth-ambiguous.
- All incoming data validated via FluentValidation before reaching the service layer. Return 400
  before any business logic executes.
- Security headers middleware: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`,
  `Permissions-Policy`.
- Rate limiting via `[EnableRateLimiting]` on all public-facing endpoints.
- Propagate `x-correlation-id` into all downstream calls and logging scope.
- DO NOT contain business logic, call repositories, construct queries, or handle secrets.

**Services (Use Cases):**
- Resource-level ownership checks (BOLA prevention) live here — never in the controller.
- Throw typed domain exceptions; never leak infrastructure error details.
- No HTTP, no Azure SDKs, no Cosmos DB, no Postgres directly. Framework-agnostic.
- `requestingUserId` is always an explicit parameter — services never reach into HTTP context.

**Repositories (Ports & Adapters):**
- All connections use `DefaultAzureCredential` / `ManagedIdentityCredential`. Never connection
  strings with embedded credentials.
- Parameterized queries only. No string interpolation in SQL or Cosmos DB queries.
- Retry on 429/503/timeouts; DO NOT retry on 401/403/404/400.
- One responsibility per repository (SRP).

**Infrastructure:**
- DI registration, bootstrap, Key Vault loading, Application Insights setup.
- Manages zero-secrets chain: Key Vault → App Configuration → `IOptions<T>`.
- DO NOT contain business logic.

### Dependency Injection Rules

- All dependencies injected via constructor parameters.
- Production code depends on interfaces, never on concrete classes.
- Every controller, service, and repository must have a corresponding interface. No exceptions.
- Mocks/fakes wired only in tests.

---
