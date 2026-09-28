---
id: skill-gitops-the-operational-model-b0bab2a443
purpose: gitops the operational model
source: src/vibey_tools/skills/plugins/azure-cloud-infra/skills/kubernetes-iac/SKILL.md
requires: ["skill-core-principle-separation-of-concerns-19153397de"]
links: ["skill-helm-chart-design-c98e31b83c"]
---

## GitOps: The Operational Model

GitOps extends declarative IaC to operations via four principles:
1. **Git as single source of truth** for all desired state
2. **Pull-based deployment** — in-cluster agent pulls changes (eliminates stored cluster credentials in CI)
3. **Continuous reconciliation** — automatically corrects drift
4. **Declarative descriptions** for everything

### Flux CD v2 vs ArgoCD — When to Choose Each

| Aspect | Flux CD v2 | ArgoCD |
|---|---|---|
| UI | None (CLI only) | Rich web dashboard with app visualization, diff views |
| Architecture | Modular Kubernetes-native controllers | Monolithic with CRDs |
| SOPS secrets | Native integration | Requires plugins |
| Kustomize + Helm | kustomize-controller as post-renderer (unique capability) | Separate paths |
| Multi-cluster | Supported | ApplicationSets with generators (Git directory, cluster, list, matrix) |
| After Weaveworks shutdown | Continues under AWS, Microsoft, community | Stable, CNCF graduated |

**Choose ArgoCD** for teams wanting UI-driven operations and easier onboarding. **Choose Flux** for platform teams wanting composable, Kubernetes-native controllers with tighter GitOps purity and native SOPS encryption.

### GitOps Repository Structure

Separate application source repos from GitOps config repos:
- **App repo**: source code + Dockerfile; CI builds images and updates the config repo
- **Config repo**: Kubernetes manifests; GitOps agent deploys from here

**Directory-based promotion on a single branch** (not branch-per-environment):
```
config-repo/
├── envs/
│   ├── dev/          # kustomization.yaml pointing to base + dev overlay
│   ├── staging/
│   └── prod/
├── base/             # shared manifests
└── platform/         # cluster-level config (RBAC, namespaces, network policies)
```

Promotion = copying version information between directories via PR. Clear visibility, easy rollback via `git revert`, no merge conflicts between environments.

---
