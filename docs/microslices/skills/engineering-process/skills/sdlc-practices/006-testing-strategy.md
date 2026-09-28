---
id: skill-testing-strategy-9d73af50bf
purpose: testing strategy
source: src/vibey_tools/skills/plugins/engineering-process/skills/sdlc-practices/SKILL.md
requires: ["skill-version-control-and-branching-eb2eac9257"]
links: ["skill-ci-cd-and-devops-83df6db94b"]
---

## Testing Strategy

### Testing Pyramid Variants
| Model | Shape | Best For |
|---|---|---|
| **Classic pyramid** (Cohn) | Many unit, fewer integration, fewest E2E | General software |
| **Trophy** (Dodds) | Integration-weighted | Modern JavaScript/React |
| **Honeycomb** (Spotify) | Service/integration-focused | Microservices |
| **Ice-cream cone (anti-pattern)** | E2E-heavy | Avoid — slow and flaky |

**Shift-left**: move testing earlier. **Shift-right**: add production observability, chaos engineering, and A/B testing.

### Unit Testing
- **Arrange-Act-Assert / Given-When-Then**; test behavior, not implementation.
- Test doubles: dummy/stub/spy/mock/fake — over-mocking couples tests to implementation.
- **Coverage**: 80% is a heuristic, not a law; line/branch/path/mutation types.
- **Mutation testing** (PIT, mutmut, Stryker): tests the tests themselves.
- **Property-based testing** (Hypothesis, fast-check): auto-discovers edge cases.

### Integration and Contract Testing
- **TestContainers**: runs real dependencies (DBs, queues) in Docker — now the integration standard.
- **Consumer-driven contract testing (Pact)**: verifies service contracts without full E2E.
- API contract validation: OpenAPI schema checks, Dredd, Schemathesis.
- DB migration testing (Flyway/Liquibase/Alembic) in CI.

### End-to-End Testing
- **Playwright (Microsoft)**: overtook Cypress as the default in mid-2024 — native cross-browser (Chromium/Firefox/WebKit), native parallelism/sharding, trace viewer; used by Amazon, Microsoft, Walmart.
- **Cypress**: retains best in-browser/time-travel debugging DX for JS-centric SPA teams.
- **Selenium**: persists in large/legacy/multi-language enterprises.
- Use the **Page Object Model**; quarantine flaky tests rather than blanket auto-retry.
- **Visual regression**: Chromatic, Percy, Playwright snapshots.

### Performance Testing
- **k6**: load-as-code, thresholds; good for CI integration.
- **Gatling**: Scala, complex flows.
- **Locust**: Python, distributed.
- Performance gates and trend tracking belong in CI; profiling (async-profiler, py-spy, pprof) and flame graphs for root cause.

### Security Testing
- **SAST**: CodeQL, SonarQube, Semgrep, Checkmarx.
- **DAST**: OWASP ZAP, Burp.
- **SCA**: Dependabot, Trivy, Snyk.
- **Secrets scanning**: gitleaks, detect-secrets, truffleHog, GitHub Secret Scanning.
- **IaC scanning**: Checkov, tfsec, KICS.
- **Container scanning**: Trivy, Grype.
- **OWASP Top 10 (2021)** anchors training.
- **Threat modeling**: STRIDE, DREAD, attack trees, PASTA.

---
