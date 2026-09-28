---
id: skill-production-staging-roadmap-a102c1539d
purpose: production staging roadmap
source: src/vibey_tools/skills/plugins/azure-cloud-infra/skills/azure-services-catalog/SKILL.md
requires: ["skill-service-retirements-act-now-9f7d89fd95"]
links: []
---

## Production Staging Roadmap

### Stage 1 — Foundation (landing zone first)
- Cloud Adoption Framework landing zone with management-group hierarchy
- Hub-spoke networking with Azure Firewall; ZRS storage defaults
- Managed identities everywhere
- Azure Policy guardrails (Audit/Deny/DeployIfNotExists)
- Bicep or Terraform IaC
- **Trigger to migrate to Virtual WAN:** exceed 2–3 active regions or ~30 spokes, or need branch/SD-WAN at scale

### Stage 2 — Compute by workload
- Default container workloads → Container Apps
- Escalate to AKS only for: Kubernetes API access, custom service mesh, multi-workload isolation, node-level control
- Functions Flex Consumption for event-driven; App Service for web apps

### Stage 3 — Data and messaging
- Map each integration to the right messaging service (don't standardize on one)
- Relational default: Azure SQL or PostgreSQL Flexible Server
- Reserve Cosmos DB for genuine global-distribution or flexible-schema needs

### Stage 4 — AI
- Build on Microsoft Foundry (Foundry projects) for new generative-AI/agent work
- Start on pay-as-you-go → move to PTU once traffic is predictable (deploy first, reserve second)
- Front all AI traffic with APIM as an AI gateway
- RAG: default to Azure AI Search

### Stage 5 — Cost
- After 30–60 days of data: Reservations on steady-state + Savings Plans on variable + Spot on fault-tolerant
- Stack Azure Hybrid Benefit
- Target high Effective Savings Rate (coverage × utilization), not maximum headline discount

### Stage 6 — Govern and observe
- Mandatory tags via Policy
- Defender for Cloud for posture
- Azure Monitor with AMA + Data Collection Rules (MMA is gone)
- Track retirements against the Azure Retirement Workbook
