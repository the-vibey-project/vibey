---
id: skill-pipeline-design-principles-9989b94a83
purpose: pipeline design principles
source: src/vibey_tools/skills/plugins/ai-and-data/skills/data-engineering/SKILL.md
requires: ["skill-elt-vs-etl-decision-framework-cfd0885cd3"]
links: ["skill-incremental-loads-cdc-b74db18ed6"]
---

## Pipeline Design Principles

- **Idempotency is non-negotiable** — re-running a job must produce the same result; enables safe backfills and retries
- **At-least-once semantics** (with idempotent writes/dedup) for most analytics; exactly-once is expensive and rarely necessary
- **Late-arriving data**: handle with watermarks and windowing
- **Late-arriving dimensions** (fact arrives before its dimension): use placeholder/inferred dimension rows rather than dropping facts or accepting null FKs
- **Watermark storage**: store in an audit table in the target DB, not just an orchestrator variable — makes it debuggable

---
