---
id: skill-helm-chart-design-c98e31b83c
purpose: helm chart design
source: src/vibey_tools/skills/plugins/azure-cloud-infra/skills/kubernetes-iac/SKILL.md
requires: ["skill-gitops-the-operational-model-b0bab2a443"]
links: ["skill-kustomize-overlays-and-patches-5480ec6daa"]
---

## Helm Chart Design

### Chart Structure
```
my-chart/
├── Chart.yaml          # metadata, version, appVersion
├── values.yaml         # defaults
├── values.schema.json  # validation schema (ALWAYS include)
├── templates/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── _helpers.tpl    # reusable named templates
│   └── NOTES.txt
├── charts/             # chart dependencies
└── .helmignore
```

### values.schema.json — Catch Misconfigurations Early

Helm validates values against this schema at install/upgrade time before anything reaches the cluster:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "properties": {
    "replicaCount": {
      "type": "integer",
      "minimum": 1
    },
    "image": {
      "type": "object",
      "properties": {
        "repository": { "type": "string" },
        "tag": { "type": "string" }
      },
      "required": ["repository", "tag"]
    }
  },
  "required": ["replicaCount", "image"]
}
```

### _helpers.tpl — Naming and Labels

Define common labels, selectors, and naming in `_helpers.tpl` and reference with `{{ include "mychart.labels" . | nindent 4 }}`. This ensures consistency and enables upgrades to find existing resources.

### Versioning and Registries

- Follow SemVer 2.0.0 strictly: MAJOR for breaking value schema changes, MINOR for new features, PATCH for fixes
- Push charts to OCI-based registries (ACR, GHCR): `helm push mychart-1.0.0.tgz oci://myregistry.azurecr.io/charts`
- Use `helm registry login` with Workload Identity or managed identity credentials

### Anti-Patterns to Avoid

- Over-templating: parameterizing everything "just in case" creates unmaintainable charts
- God charts: one chart for an entire platform with dozens of conditionally-enabled components
- `:latest` tags in default values — breaks reproducibility and rollback
- Not using `.helmignore` — test files bloat packaged charts

---
