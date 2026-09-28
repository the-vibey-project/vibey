---
id: skill-compute-decision-ladder-2026-default-fe76b03cac
purpose: compute decision ladder 2026 default
source: src/vibey_tools/skills/plugins/software-architecture/skills/architecture-patterns/SKILL.md
requires: ["skill-core-principle-3aa446b8c0"]
links: ["skill-monolithic-architecture-33981d97e4"]
---

## Compute Decision Ladder (2026 Default)
```
App Service (modular monolith)
    → Azure Container Apps (serverless containers — simpler default for most containerized workloads)
        → AKS (full Kubernetes only when you need the API, operators, mesh, or fine-grained node control)
```
Azure Functions Flex Consumption fills the event-driven serverless tier.
