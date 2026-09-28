---
id: skill-database-migrations-in-ci-d37ba1492b
purpose: database migrations in ci
source: src/vibey_tools/skills/plugins/devsecops-cicd/skills/cicd-field-guide/SKILL.md
requires: ["skill-testing-in-ci-cd-43013e4028"]
links: ["skill-ai-assisted-ci-cd-5e66af1cce"]
---

## Database Migrations in CI

- Tools: Flyway/Liquibase/Alembic/golang-migrate
- **Expand-contract (backward-compatible) migrations** are mandatory for zero-downtime and blue-green compatibility
- Test migrations in pipelines
- Prefer forward-only in many SaaS contexts

---
