---
id: skill-etl-vs-elt-a0c0cb6803
purpose: etl vs elt
source: src/vibey_tools/skills/plugins/software-architecture/skills/architecture-patterns/SKILL.md
requires: ["skill-encryption-eb57256b0d"]
links: ["skill-stream-processing-772cdadbc0"]
---

## ETL vs ELT
- **ETL**: transforms before load (legacy, for constrained targets)
- **ELT**: loads raw, transforms in place (modern default — leverage cloud compute)
- **Azure Data Factory**: ETL/ELT orchestration, mapping data flows, Copy activity
