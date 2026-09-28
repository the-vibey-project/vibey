---
id: skill-quality-gates-and-exception-process-bf37182081
purpose: quality gates and exception process
source: src/vibey_tools/skills/plugins/devsecops-cicd/skills/devsecops-pipeline/SKILL.md
requires: ["skill-semgrep-posttooluse-hook-for-real-time-scanning-f1f93ddada"]
links: ["skill-dast-owasp-zap-for-deployed-environments-367c40e4c3"]
---

## Quality Gates and Exception Process

**Gate thresholds:**
- SAST: fail on HIGH or CRITICAL severity findings
- SCA: fail on HIGH or CRITICAL CVEs
- Secrets: fail on any detected secret
- Container: fail on CRITICAL or HIGH CVEs in base image or installed packages
- IaC: fail on HIGH severity policy violations (MEDIUM as warning only)

**Exceptions process:**
1. Security engineer reviews the finding
2. Documents justification in code comment or exceptions file
3. Uses tool-specific suppression annotation:

```csharp
// Semgrep suppression
var query = $"SELECT * FROM Users WHERE Id = {userId}";  // nosemgrep: sql-injection
// EXCEPTION: userId is validated as integer before this point — confirmed 2026-01-15

// Trivy suppression (in Trivy config file)
// trivy:ignore:CVE-2024-12345
```

```yaml
# Checkov suppression inline
resource "azurerm_storage_account" "main" {
  # checkov:skip=CKV_AZURE_33: Public access needed for CDN static assets — reviewed 2026-01-15
  allow_nested_items_to_be_public = true
}
```

---
