---
id: skill-kustomize-overlays-and-patches-5480ec6daa
purpose: kustomize overlays and patches
source: src/vibey_tools/skills/plugins/azure-cloud-infra/skills/kubernetes-iac/SKILL.md
requires: ["skill-helm-chart-design-c98e31b83c"]
links: ["skill-terraform-for-aks-provisioning-20b00e2bbb"]
---

## Kustomize: Overlays and Patches

### Base + Overlay Pattern

```
kubernetes/
├── base/
│   ├── deployment.yaml
│   ├── service.yaml
│   └── kustomization.yaml
└── overlays/
    ├── dev/
    │   ├── kustomization.yaml      # references ../base
    │   └── patches/
    │       └── deployment-replicas.yaml
    ├── staging/
    │   └── kustomization.yaml
    └── prod/
        └── kustomization.yaml
```

**base/kustomization.yaml:**
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - deployment.yaml
  - service.yaml
```

**overlays/prod/kustomization.yaml:**
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: myapp-prod
resources:
  - ../../base
patches:
  - path: patches/deployment-prod.yaml
images:
  - name: myapp
    newTag: "1.2.3"
```

**Keep namespace declarations out of base resources.** Specify namespaces in overlay `kustomization.yaml` files so the base is reusable across environments without modification.

### ConfigMapGenerator — Automatic Rolling Updates

ConfigMapGenerator creates resources with content-hash suffixed names, automatically triggering rolling updates when content changes:

```yaml
configMapGenerator:
  - name: app-config
    envs:
      - .env.prod
    literals:
      - LOG_LEVEL=info

secretGenerator:
  - name: db-credentials
    files:
      - password.txt
```

This is a critical advantage over manually managed ConfigMaps — no more "did the deployment pick up the config change?"

### Strategic Merge Patches

```yaml
# patches/deployment-prod.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: myapp
        resources:
          requests:
            cpu: "500m"
            memory: "512Mi"
          limits:
            memory: "512Mi"
```

### Kustomize + Helm Combined

Flux's kustomize-controller can post-render Helm output with Kustomize patches — combine both tools in a single pipeline. Use Helm for third-party charts (Prometheus, NGINX, cert-manager) and Kustomize for overlaying environment-specific patches.

---
