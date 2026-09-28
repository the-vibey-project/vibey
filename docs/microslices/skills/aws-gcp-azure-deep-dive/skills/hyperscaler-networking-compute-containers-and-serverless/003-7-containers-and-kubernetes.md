---
id: skill-7-containers-and-kubernetes-5a6b6757bd
purpose: 7 containers and kubernetes
source: src/vibey_tools/skills/plugins/aws-gcp-azure-deep-dive/skills/hyperscaler-networking-compute-containers-and-serverless/SKILL.md
requires: ["skill-6-compute-ebfbe0e368"]
links: ["skill-8-serverless-cd3ad0f337"]
---

## §7. Containers and Kubernetes

```
Managed K8s     EKS              AKS              ⚠️ GKE
Serverless K8s  ⚠️ Fargate        ACI / AKS Auto   GKE Autopilot
Registry        ECR              ACR              Artifact Registry
Simple runner   App Runner       Container Apps   ⚠️ Cloud Run
```
> **⚠️ GKE is the strongest managed Kubernetes of the three, and this is not a close
> call.** ⚠️ **Google originated Kubernetes; GKE has the most mature autoscaling
> (including node auto-provisioning), the best upgrade handling, and Autopilot removes
> node management entirely.** **EKS has improved substantially but historically required
> more assembly — add-ons, IRSA setup, networking plugins.** **AKS sits between them and
> integrates well with Entra.**

**⚠️ The question worth asking before any of this**: **do you actually need Kubernetes?**
⚠️ **For a small number of services, Cloud Run / Container Apps / App Runner deliver most
of the benefit at a fraction of the operational cost.** **Kubernetes pays off at
organizational scale — many teams, many services, needing a common platform** —
⚠️ **and below that threshold it is usually a substantial and unnecessary operational tax.**

---
