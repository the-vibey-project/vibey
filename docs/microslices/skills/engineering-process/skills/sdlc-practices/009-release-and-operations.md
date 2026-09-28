---
id: skill-release-and-operations-fe87400815
purpose: release and operations
source: src/vibey_tools/skills/plugins/engineering-process/skills/sdlc-practices/SKILL.md
requires: ["skill-code-quality-and-tech-debt-54b22f1b74"]
links: ["skill-observability-c2dfad5042"]
---

## Release and Operations

### Versioning and Releases
- **SemVer** (MAJOR.MINOR.PATCH) automated via semantic-release/release-please.
- Changelogs generated from Conventional Commits.
- Release trains vs. continuous delivery; feature freezes signal either genuine stabilization needs or accumulated debt.

### Database Change Management
- Tools: Flyway, Liquibase, Alembic, golang-migrate.
- **Expand-contract pattern**: for zero-downtime schema changes.

### Incident Management
- **Blameless postmortems**: 5 Whys, timeline reconstruction.
- **Severity levels**: P0–P4 with response SLAs.
- **Error budgets and SLI/SLO/SLA hierarchy** (SRE).
- **Chaos engineering**: Chaos Monkey, AWS FIS, Azure Chaos Studio.
- Sustainable on-call rotations with runbooks and escalation paths.

---
