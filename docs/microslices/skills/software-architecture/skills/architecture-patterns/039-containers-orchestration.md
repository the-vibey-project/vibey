---
id: skill-containers-orchestration-539c50bde7
purpose: containers orchestration
source: src/vibey_tools/skills/plugins/software-architecture/skills/architecture-patterns/SKILL.md
requires: ["skill-hybrid-integration-b59461eb2c"]
links: ["skill-gitops-a3842ff806"]
---

## Containers & Orchestration

**ACA KEDA gotcha:** Scale-to-zero with Service Bus can scale down prematurely when messages process faster than the polling interval — lower `pollingInterval` or set `minReplicas: 1` for steady low-frequency traffic. KEDA's default cooldown is 300s.

**AKS node pool types:** Azure CNI (standard), Azure CNI Overlay (scalable), Azure CNI Powered by Cilium (note: incompatible with Istio add-on).
