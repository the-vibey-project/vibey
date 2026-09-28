---
id: skill-lambda-vs-kappa-fcaa1ad17d
purpose: lambda vs kappa
source: src/vibey_tools/skills/plugins/software-architecture/skills/architecture-patterns/SKILL.md
requires: ["skill-stream-processing-772cdadbc0"]
links: ["skill-cdc-change-data-capture-3405ab4c9e"]
---

## Lambda vs Kappa
- **Lambda**: batch (accurate) + speed (real-time) + serving layers — two code paths to maintain
- **Kappa**: single stream path with replay — simpler operationally
- **Modern recommendation**: Kappa with Event Hubs + Databricks Structured Streaming + Delta Lake
