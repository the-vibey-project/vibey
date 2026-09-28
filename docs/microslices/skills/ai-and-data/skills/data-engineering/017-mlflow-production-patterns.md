---
id: skill-mlflow-production-patterns-be157f33f1
purpose: mlflow production patterns
source: src/vibey_tools/skills/plugins/ai-and-data/skills/data-engineering/SKILL.md
requires: ["skill-feature-stores-012d8cc2ed"]
links: ["skill-ml-modeling-best-practices-0d85ee4a54"]
---

## MLflow — Production Patterns

Four components: **Tracking** (log params/metrics/artifacts per run), **Projects** (reproducible packaging), **Models** (flavors for deployment), **Model Registry** (versioning + lineage + lifecycle).

**Modern champion/challenger pattern (MLflow 2.9.0+):**
- Fixed stages (`Staging/Production/Archived`) are deprecated
- Use **aliases**: mutable named pointers like `champion`/`challenger`
- Reference: `models:/MyModel@champion`
- Promote by reassigning the alias

**Production deployment patterns:**
- Batch scoring for non-latency-sensitive use
- Online inference behind managed endpoint for real-time
- **Shadow mode**: run new model on live traffic without acting, before promotion
- **Champion/challenger**: controlled rollout via alias reassignment

---
