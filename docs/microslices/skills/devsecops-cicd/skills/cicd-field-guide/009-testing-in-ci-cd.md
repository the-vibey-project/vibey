---
id: skill-testing-in-ci-cd-43013e4028
purpose: testing in ci cd
source: src/vibey_tools/skills/plugins/devsecops-cicd/skills/cicd-field-guide/SKILL.md
requires: ["skill-monorepo-ci-cd-at-scale-15bf54a5c2"]
links: ["skill-database-migrations-in-ci-d37ba1492b"]
---

## Testing in CI/CD

- **Test pyramid:** unit → integration → contract → E2E
- **Parallelization/splitting:** platform-native or tools like Jest `--shard`
- **Consumer-driven contract testing:** Pact
- **Visual regression:** Chromatic/Percy/Playwright
- **Performance:** k6/Gatling/Locust
- **Flaky-test management:** detect via quarantine and flakiness scoring; fix root causes; use auto-retry sparingly (masks real bugs)
- **Ephemeral environments per PR:** Review Apps, Neon/PlanetScale DB branching, Testcontainers for portable integration dependencies

---
