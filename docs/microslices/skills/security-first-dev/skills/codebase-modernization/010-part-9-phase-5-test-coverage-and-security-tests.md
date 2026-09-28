---
id: skill-part-9-phase-5-test-coverage-and-security-tests-b1cf602c1b
purpose: part 9 phase 5 test coverage and security tests
source: src/vibey_tools/skills/plugins/security-first-dev/skills/codebase-modernization/SKILL.md
requires: ["skill-part-8-phase-4-architecture-refactoring-p3-priority-a0edb5dc21"]
links: ["skill-part-10-phase-6-logging-and-observability-823177b59f"]
---

## PART 9: PHASE 5 — TEST COVERAGE AND SECURITY TESTS

When inheriting a codebase with low coverage, do not try to achieve 80% in one sprint. Add
tests in this priority order:

1. Security tests first — auth bypass, BOLA, injection (even for code not being changed)
2. Tests for code you are about to change — write characterization tests before refactoring
3. Critical business logic — paths that, if broken, cause financial loss or data corruption
4. Error paths — 4xx and 5xx responses
5. Happy path coverage — fill in remaining gaps

### 9.1 Characterization Tests (Before Refactoring Untested Code)

```csharp
[Fact]
[Trait("Type", "Characterization")]
public async Task CreateOrder_ExistingBehavior_ReturnsCreatedWithCurrentLogic()
{
    // Documents what the code CURRENTLY does before you change it
    // TODO: [TICKET-123] Replace with proper TDD test after service extraction
}
```

### 9.2 Security Test Template for Existing Endpoints

```csharp
[Fact]
public async Task GetById_NoAuthToken_Returns401() { ... }
[Fact]
public async Task GetById_ExpiredToken_Returns401() { ... }
[Fact]
public async Task GetById_WrongRole_Returns403() { ... }
[Fact]
public async Task GetById_ValidTokenButNotOwner_Returns403() { /* BOLA test */ }
[Theory]
[InlineData("'; DROP TABLE orders; --")]
[InlineData("<script>alert('xss')</script>")]
[InlineData("../../../etc/passwd")]
public async Task CreateOrder_AdversarialInput_Returns400(string maliciousInput) { ... }
```

### 9.3 Coverage Gates — Introduce Incrementally

Do not set coverage gates to 80% on a codebase with 20% coverage. Set it at current + 5%,
ratchet up each sprint. The coverage gate should **never decrease**.

```xml
<!-- .runsettings — adjust minimum to current actual coverage -->
<CoverageThreshold>
  <LineCoverage minimum="35" />  <!-- start at actual; increase 5% each sprint -->
</CoverageThreshold>
```

---
