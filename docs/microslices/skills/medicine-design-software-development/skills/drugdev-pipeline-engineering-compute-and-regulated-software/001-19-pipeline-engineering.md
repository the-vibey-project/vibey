---
id: skill-19-pipeline-engineering-06c46e5e37
purpose: 19 pipeline engineering
source: src/vibey_tools/skills/plugins/medicine-design-software-development/skills/drugdev-pipeline-engineering-compute-and-regulated-software/SKILL.md
requires: []
links: ["skill-20-compute-9980680245"]
---

## §19. Pipeline Engineering

**⚠️ Workflow orchestration**: **Nextflow and Snakemake (⚠️ the bioinformatics standards,
container-friendly and resumable), Airflow/Prefect/Dagster (⚠️ general-purpose, better for
scheduled production work), and ⚠️ the practical requirement that long-running scientific
jobs must be RESUMABLE — a 200-hour simulation that fails at hour 190 must not restart.**
**⚠️ Data engineering specifics**: **⚠️ chemical databases need structure search (RDKit's
PostgreSQL cartridge, or a dedicated chemical database), ⚠️ InChIKey as the join key
(§4 → `drugdev-representation-cheminformatics-data-quality-and-leakage`), and provenance tracking on every derived value.**
**⚠️ The architectural pattern that works**: ⚠️ **separate the SCIENCE (a pure function
from molecule to prediction) from the ORCHESTRATION and the STORAGE** — **because the
science changes fast, the models get retrained constantly, and mixing them makes both
untestable.**
**⚠️ Model registry and versioning is not optional** ⚠️ **when a number may end up in a
regulatory submission** (§22): **you must be able to say which model version, trained on
which data, produced a given prediction on a given date.**

---
