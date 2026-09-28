---
id: skill-test-shape-models-match-your-architecture-642ec36b9c
purpose: test shape models match your architecture
source: src/vibey_tools/skills/plugins/quality-engineering/skills/test-strategy/SKILL.md
requires: []
links: ["skill-smurf-test-portfolio-health-evaluation-c360743786"]
---

## Test Shape Models: Match Your Architecture

The right test distribution is determined by your system architecture, not by dogma. Three models plus one risk framework:

### Test Pyramid (Cohn/Fowler)
```
        /\
       /E2\        ← Narrow: expensive, slow, flaky — use sparingly
      /----\
     / Int  \      ← Middle layer: module interactions
    /--------\
   / Unit     \    ← Wide base: fast, isolated, cheap
  /____________\
```

**Best for: monolithic applications** where unit-level isolation is cheap and highly informative.

- **Unit tests (60–70%):** Test single functions or classes in complete isolation. Fast (< 5 ms each), deterministic, no I/O.
- **Integration tests (20–30%):** Test module interactions, database queries, API layer behavior. Use testcontainers or emulators.
- **E2E tests (5–10%):** Test critical user journeys end-to-end. Reserve for highest-value paths only.

### Testing Trophy (Kent C. Dodds)
```
          /\
         /E2\
        /----\
       / Inte-\    ← LARGEST LAYER: integration tests dominate
      / gration\
     /----------\
    /  Unit      \
   /--------------\
  / Static Analysis\  ← Foundation: linting, type checking
 /___________________\
```

**Best for: API-centric and frontend-heavy applications.**

Key insight (Guillermo Rauch): "The more your tests resemble the way your software is used, the more confidence they can give you." For APIs, an integration test that calls through the HTTP layer with a real database gives far more confidence than 20 unit tests on isolated functions.

### Honeycomb Model (Spotify)
```
     ○ ○ ○ ○ ○    ← E2E: minimal, highest-value journeys only
  ○ ○ ○ ○ ○ ○ ○
 ○ ○ ○ INTEGRA- ○ ← Dominates: inter-service is the main risk
 ○ ○ TION ○ ○ ○ ○
  ○ ○ ○ ○ ○ ○ ○
     ○ ○ ○ ○ ○    ← Unit: only for isolated business logic
```

**Best for: microservices architectures.**

Unit tests for pure business logic (algorithms, transformations, domain rules). Integration tests for everything involving service boundaries — database queries, message queues, HTTP clients. E2E tests only for the most critical cross-service user journeys.

**Why Honeycomb:** In microservices, the complexity lives *between* services. A unit test of the order service tells you nothing about whether it integrates correctly with inventory. The inter-service integration is where bugs live.

### Swiss Cheese Model (James Reason, 1990)

The Swiss Cheese model is not a distribution — it is a **risk framework** for explaining why layered testing is necessary. Use this with stakeholders.

```
Static  Unit  Integration  Contract  E2E   Monitoring
  |       |       |           |       |        |
 [■■□■]  [■□■■]  [□■■■]     [■■□■]  [■□□■]   [■■■□]
  
Defects escape to production only when holes align across ALL layers.
```

Each layer has gaps (the "holes"):
- **Static analysis** catches syntax, type errors, security patterns — but not logic bugs
- **Unit tests** catch function-level logic — but not integration failures
- **Integration tests** catch component interaction bugs — but not cross-service contract violations
- **Contract tests** catch API compatibility — but not full user journey failures
- **E2E tests** catch journey-level failures — but are too slow/brittle to run on everything
- **Production monitoring** catches what everything else missed — but after users are affected

No single layer is sufficient. Defects escape when holes align. The goal is to ensure holes rarely align.

**Use this model in risk conversations:** "We don't have contract tests, which means our Swiss Cheese model has a full hole in that layer. Any provider API change will escape through to production."

---
