---
id: skill-conway-s-law-8fd789c39a
purpose: conway s law
source: src/vibey_tools/skills/plugins/software-architecture/skills/architecture-patterns/SKILL.md
requires: ["skill-make-vs-buy-vs-configure-083116781f"]
links: []
---

## Conway's Law
Systems mirror team communication structure. The **Inverse Conway Maneuver** designs team structure to produce the desired architecture. **Team Topologies**: stream-aligned, platform, enabling, complicated-subsystem teams.

---

# STAGED ROLLOUT GUIDANCE

**Stage 1 — Start simple.**
- Modular monolith on **App Service** with deployment slots
- Azure SQL or PostgreSQL Flexible Server (with PgBouncer)
- Key Vault references for secrets
- App Insights via the OpenTelemetry distro from day one
- Write ADRs for irreversible choices
- *Advance when:* measurable deployment contention or a subsystem with a distinct scaling/availability profile

**Stage 2 — Decompose deliberately.**
- Move to **ACA** (not AKS) for first microservices — KEDA + Dapr without cluster ops
- **Service Bus** for async; **Outbox pattern** to avoid dual writes
- **APIM** as the front door; database-per-service
- *Advance to AKS when:* full Kubernetes API, custom operators, service mesh, or fine-grained node/GPU control

**Stage 3 — Scale and harden.**
- AKS + **Istio add-on** for mTLS (plan CNI — not Cilium); **Workload Identity** + CSI secrets; **Flux** for GitOps
- Availability Zones everywhere; multi-region only once SLO crosses ~99.95%
- Pair Retry + Circuit Breaker; Queue-Based Load Leveling + Competing Consumers
- Define RTO/RPO before choosing geo-replication topology

**Stage 4 — Add AI-native capability.**
- RAG: **Azure AI Search** (`vector_semantic_hybrid`) + Azure OpenAI; co-locate vectors in Cosmos DB/Azure SQL to avoid a separate service
- **APIM AI Gateway** (token limits, semantic caching, PTU→PAYG spillover) on day one
- Agents: **Foundry Agent Service** (GA) + **Microsoft Agent Framework** (GA targeted end of Q1 2026)
- **Migrate off Prompt Flow before April 20, 2027**

---

# PLATFORM MIGRATIONS TO SCHEDULE NOW

| Migration | Deadline |
|---|---|
| Front Door classic → Standard/Premium | March 31, 2027 |
| Azure CDN classic → Front Door | September 30, 2027 |
| AzureML SDK v1 → v2 | June 30, 2026 |
| Linux Consumption Functions → Flex Consumption | September 30, 2028 |
| In-process .NET Functions model → isolated | November 2026 |
| Semantic Kernel / AutoGen → Microsoft Agent Framework | Before GA (end Q1 2026) |
| Prompt Flow → Microsoft Agent Framework | Before April 20, 2027 |
| Analytics → Microsoft Fabric / OneLake (medallion) | Ongoing |
