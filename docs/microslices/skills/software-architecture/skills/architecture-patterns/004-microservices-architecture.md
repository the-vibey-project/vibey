---
id: skill-microservices-architecture-62fbe9e8e4
purpose: microservices architecture
source: src/vibey_tools/skills/plugins/software-architecture/skills/architecture-patterns/SKILL.md
requires: ["skill-monolithic-architecture-33981d97e4"]
links: ["skill-serverless-architecture-6e3a8ced63"]
---

## Microservices Architecture

**Azure mapping:**
- **Azure Container Apps (ACA)**: serverless Kubernetes abstraction with KEDA and Dapr built in; the right default for most microservices
- **AKS**: managed Kubernetes when you need the full API; **Istio-based service mesh add-on** is Microsoft-supported (managed istiod, AZ-aware, integrates with Managed Prometheus/Grafana)
- **Service Bus** for async; **APIM** as the front door

**AKS Istio add-on constraints:**
- Does NOT work on clusters using **Azure CNI Powered by Cilium**
- Does NOT work alongside the deprecated OSM add-on or self-managed Istio
- Does NOT yet support sidecar-less **Ambient** mode
- Blocks `EnvoyFilter`, `WasmPlugin`, `IstioOperator`, and several other CRDs

**Production gotchas:**
- A **shared database violates the pattern** and silently recouples teams
- **Anti-pattern:** distributed monolith — services deployed in lockstep

**Decision trigger:** Independent deployability or scaling of a subsystem is a hard requirement, and you have the platform/observability maturity to pay the distributed-systems tax.
