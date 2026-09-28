---
id: skill-environment-promotion-pattern-176e8946c7
purpose: environment promotion pattern
source: src/vibey_tools/skills/plugins/azure-cloud-infra/skills/kubernetes-iac/SKILL.md
requires: ["skill-upgrade-strategy-6b3449855a"]
links: ["skill-production-workload-checklist-0c887abb40"]
---

## Environment Promotion Pattern

**Dev → Staging → Prod via overlay promotion:**

1. CI builds image, tags it with git SHA: `myapp:abc1234`
2. CI updates the image tag in `envs/dev/kustomization.yaml` via PR
3. GitOps agent deploys to dev
4. Validate in dev, promote: update `envs/staging/kustomization.yaml` via PR
5. Validate in staging, promote: update `envs/prod/kustomization.yaml` via PR with required approvals

**With ArgoCD ApplicationSets:**
```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: myapp
spec:
  generators:
  - list:
      elements:
      - cluster: dev
        url: https://dev-aks.example.com
      - cluster: staging
        url: https://staging-aks.example.com
      - cluster: prod
        url: https://prod-aks.example.com
  template:
    metadata:
      name: 'myapp-{{cluster}}'
    spec:
      source:
        repoURL: https://github.com/myorg/config-repo
        path: 'envs/{{cluster}}'
      destination:
        server: '{{url}}'
        namespace: myapp
```

---
