---
id: skill-branch-protection-rules-a96e1c9d00
purpose: branch protection rules
source: src/vibey_tools/skills/plugins/devsecops-cicd/skills/devsecops-pipeline/SKILL.md
requires: ["skill-secrets-management-no-hardcoded-credentials-121c3aa354"]
links: ["skill-reusable-security-workflow-pattern-66034e170e"]
---

## Branch Protection Rules

Configure these on the main branch to enforce security gates before merge:

```yaml
# Via GitHub repository settings or Terraform:
resource "github_branch_protection" "main" {
  repository_id = github_repository.main.node_id
  pattern       = "main"

  required_status_checks {
    strict   = true    # Require branch to be up to date
    contexts = [
      "SAST (Semgrep)",
      "SAST (CodeQL)",
      "SCA (Snyk)",
      "Secrets Scan (Gitleaks)",
      "Container Scan (Trivy)",
      "IaC Scan (Checkov)",
    ]
  }

  required_pull_request_reviews {
    dismiss_stale_reviews           = true
    require_code_owner_reviews      = true
    required_approving_review_count = 1
  }

  enforce_admins = true    # Admins cannot bypass checks
}
```

---
