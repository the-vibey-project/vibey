---
id: skill-iac-in-pipelines-3b733bb3b9
purpose: iac in pipelines
source: src/vibey_tools/skills/plugins/devsecops-cicd/skills/cicd-field-guide/SKILL.md
requires: ["skill-platform-engineering-and-internal-developer-platforms-c5e6326e9d"]
links: ["skill-staged-implementation-roadmap-a978d36de3"]
---

## IaC in Pipelines

- Pattern: **plan → approval gate → apply**
- `terraform plan` in CI for drift detection
- Testing: Terratest/Pester
- Scanning: Checkov/tfsec/KICS
- Principle: immutable infrastructure (replace, don't patch)

---
