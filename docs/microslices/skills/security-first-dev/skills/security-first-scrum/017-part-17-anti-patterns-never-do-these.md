---
id: skill-part-17-anti-patterns-never-do-these-3768dcb030
purpose: part 17 anti patterns never do these
source: src/vibey_tools/skills/plugins/security-first-dev/skills/security-first-scrum/SKILL.md
requires: ["skill-part-16-definition-of-done-d3955a0697"]
links: ["skill-part-18-structured-logging-standards-6f25a47833"]
---

## PART 17: ANTI-PATTERNS — NEVER DO THESE

### Security Anti-Patterns (Highest Severity)

- Hardcoding any credential, key, connection string, or secret anywhere in source code
- Using `AllowAnyOrigin()` in CORS configuration
- Storing tokens in `localStorage` — always `sessionStorage` or in-memory
- Creating `PublicClientApplication` inside a React component (re-created on every render)
- Enabling implicit grant on any app registration
- Sharing a single app registration across environments
- SQL query with string interpolation using user-supplied data
- `dangerouslySetInnerHTML` without DOMPurify sanitization
- `TypeNameHandling = TypeNameHandling.All` in JSON deserialization
- `MD5.Create()` for any security-sensitive purpose
- Exposing Swagger / SwaggerUI in any non-Development environment
- A controller action without explicit `[Authorize]` or `[AllowAnonymous]`
- Logging JWTs, passwords, API keys, PII, or connection strings at any log level
- Bypassing or soft-failing any security gate in CI to unblock deployment
- Using connection strings with embedded keys for any Azure service
- Using Azure control-plane roles as a substitute for data-plane RBAC
- `UseAuthentication()` placed after `UseAuthorization()` in the middleware pipeline
- Retrying on 401 or 403 responses (permanent failures, never transient)
- Resource-level authorization (BOLA check) placed in the controller instead of the service
- Sharing Managed Identities across services with different trust requirements
- Using Pod Identity in AKS (deprecated, EOL September 2025) — use Workload Identity

### Architecture Anti-Patterns

- Business logic in a controller or Blazor page
- Controller, service, or repository without a corresponding interface
- Direct repository call from a controller (bypasses service layer)
- Importing a concrete repository class into a service
- Domain model importing from infrastructure, EF Core, or Azure SDKs
- Circular dependencies between layers

### Testing Anti-Patterns

- Writing implementation before a failing test
- Testing implementation details instead of behavior
- Mocking the class under test
- Using production Azure resources in unit tests
- Tests that depend on execution order
- Omitting the adversarial / negative security test case

### Code Quality Anti-Patterns

- `catch (Exception) { }` or swallowing exceptions silently
- Magic numbers / strings without named constants
- Methods longer than ~50 lines
- `async void` methods (except Blazor event callbacks where unavoidable)
- Blocking on async code (`.Result`, `.Wait()`) — always `await`
- Commented-out code committed to the repository

### Agentic Anti-Patterns

- Generating large blocks of code without running tests
- Modifying multiple layers at once without verifying each layer
- Skipping the interface step and going straight to implementation
- Assuming security requirements when they are not explicit in the spec — surface the gap
- Leaving the codebase in a broken state between steps
- Suggesting a deadline workaround that involves bypassing a security control
- Treating "it's behind the firewall" as a security argument — Zero Trust applies everywhere

---
