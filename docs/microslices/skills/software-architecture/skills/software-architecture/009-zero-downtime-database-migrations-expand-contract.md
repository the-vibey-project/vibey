---
id: skill-zero-downtime-database-migrations-expand-contract-0fdb3b3664
purpose: zero downtime database migrations expand contract
source: src/vibey_tools/skills/plugins/software-architecture/skills/software-architecture/SKILL.md
requires: ["skill-observability-54fe73659e"]
links: ["skill-ci-cd-010861d9fe"]
---

## Zero-Downtime Database Migrations (Expand-Contract)

**Core technique for rolling deployments (multiple pods run old + new code simultaneously):**

1. **Phase 1 EXPAND**: Add new column as nullable; deploy code that reads both old and new (backward-compatible)
2. **Phase 2 MIGRATE**: Backfill new column; verify 100%
3. **Phase 3 CONTRACT**: Add NOT NULL, drop old column; deploy code using only new column

**Never rename/drop a column while old code still runs.**

**Alembic on Postgres operational must-dos:**
- Set `transaction_per_migration=True`
- Set short `lock_timeout` (~4s) — migration fails fast rather than queuing every query behind `AccessExclusiveLock`
- Set `statement_timeout` as safety net
- Create indexes with `CONCURRENTLY`
- Add constraints with `NOT VALID` then `VALIDATE`
- Use `alembic check` in CI to block PRs that change models without a migration
- **Never let multiple pods race `alembic upgrade head`** — run migrations as a dedicated step/init-container before new code starts

---
