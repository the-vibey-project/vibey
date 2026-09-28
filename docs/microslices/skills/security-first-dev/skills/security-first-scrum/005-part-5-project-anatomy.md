---
id: skill-part-5-project-anatomy-c6ec05eefa
purpose: part 5 project anatomy
source: src/vibey_tools/skills/plugins/security-first-dev/skills/security-first-scrum/SKILL.md
requires: ["skill-part-4-spec-driven-development-7e7a48e97d"]
links: ["skill-part-6-onion-architecture-strict-layer-rules-d550544859"]
---

## PART 5: PROJECT ANATOMY

### .NET Web API

```
src/
  <Service>.Api/
    Controllers/           <- ASP.NET Core controllers (entry points only)
      Interfaces/          <- Controller interfaces
    Middleware/            <- Exception handling, correlation-id, security headers
  <Service>.Application/
    Contracts/             <- Request/response DTOs, FluentValidation validators
    Services/              <- Business logic, use-cases, orchestration
      Interfaces/          <- Service interfaces (ports)
  <Service>.Domain/
    Models/                <- Domain entities, value objects, enums
    Exceptions/            <- Typed exception hierarchy
  <Service>.Infrastructure/
    Repositories/          <- Cosmos DB, PostgreSQL, Azure Service Bus adapters
      Interfaces/          <- Repository interfaces (ports)
      Mocks/               <- In-memory / fake implementations for testing
    Config/                <- Azure App Configuration, Key Vault, options classes
    Logging/               <- Application Insights / structured logging setup
    DependencyInjection/   <- DI registration extensions

tests/
  Unit/ Integration/ Contract/ E2E/ Fixtures/ Security/
```

### React Web App

```
src/
  api/          <- Axios interceptors, typed contracts, MSAL token injection
  components/   <- Reusable UI
  features/     <- Feature-scoped modules
  hooks/        <- Shared custom hooks
  models/       <- TypeScript interfaces mirroring API contracts
  services/     <- Client-side business logic
  infrastructure/ <- Auth (MSAL), config, telemetry
  security/     <- ProtectedRoute, DOMPurify wrappers, CSP helpers
tests/
  unit/ integration/ e2e/ security/
```

### Databricks ETL Pipeline

```
src/
  pipelines/<pipeline_name>/
    contracts/        <- Pydantic / dataclass schemas
    transformations/  <- Pure transformation functions (no I/O)
    readers/          <- Source adapters
    writers/          <- Sink adapters
    orchestration/    <- Entry point, step sequencing
  shared/
    security/         <- Secret resolution helpers, Unity Catalog access wrappers
tests/
  unit/ integration/ contract/ security/
```

---
