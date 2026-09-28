---
id: skill-reusable-security-workflow-pattern-66034e170e
purpose: reusable security workflow pattern
source: src/vibey_tools/skills/plugins/devsecops-cicd/skills/devsecops-pipeline/SKILL.md
requires: ["skill-branch-protection-rules-a96e1c9d00"]
links: ["skill-security-policy-as-code-with-opa-rego-d02d9ec443"]
---

## Reusable Security Workflow Pattern

Extract scanning jobs into reusable workflows for consistent security across all repositories:

```yaml
# .github/workflows/security-scan.yml (in a central org repo)
on:
  workflow_call:
    inputs:
      image-ref:
        required: true
        type: string
      infra-directory:
        required: false
        type: string
        default: 'infra/'
    secrets:
      SNYK_TOKEN:
        required: true

jobs:
  sast:
    uses: ./.github/workflows/sast.yml
  sca:
    uses: ./.github/workflows/sca.yml
    secrets: inherit
  container-scan:
    uses: ./.github/workflows/container-scan.yml
    with:
      image-ref: ${{ inputs.image-ref }}
```

Call from any repository:
```yaml
security:
  uses: myorg/shared-workflows/.github/workflows/security-scan.yml@main
  with:
    image-ref: myapp:${{ github.sha }}
    infra-directory: infrastructure/
  secrets: inherit
```

---
