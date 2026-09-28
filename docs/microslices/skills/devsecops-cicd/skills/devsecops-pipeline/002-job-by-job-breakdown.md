---
id: skill-job-by-job-breakdown-a1bcf6b459
purpose: job by job breakdown
source: src/vibey_tools/skills/plugins/devsecops-cicd/skills/devsecops-pipeline/SKILL.md
requires: ["skill-the-full-6-job-github-actions-pipeline-b6e5ccb08a"]
links: ["skill-semgrep-posttooluse-hook-for-real-time-scanning-f1f93ddada"]
---

## Job-by-Job Breakdown

### Job 1: SAST — Static Application Security Testing

Two tools for different strengths:

**Semgrep** — best for custom rules and rapid rule authorship. Rulesets to enable:
- `p/security-audit` — broad security patterns
- `p/owasp-top-ten` — OWASP Top 10 checks
- `p/csharp` — C#-specific patterns
- `p/typescript` — TypeScript/React patterns
- `p/secrets` — hardcoded credential detection

**CodeQL** — best for C# and TypeScript deep semantic analysis. Finds:
- SQL injection (including EF Core string interpolation)
- Cross-site scripting
- Path traversal
- Insecure deserialization
- Missing authorization

Use `languages: csharp, javascript` and `queries: security-extended` for the most thorough analysis. `autobuild` handles .NET solution files automatically.

Both tools upload SARIF results to GitHub's Security tab. Results persist and can be reviewed even if the job fails — always use `if: always()` on SARIF upload steps.

### Job 2: SCA — Software Composition Analysis

Snyk scans dependency trees for known vulnerabilities (CVEs) in NuGet and npm packages.

`--severity-threshold=high` fails the job on HIGH or CRITICAL findings. Use `--all-projects` for monorepo solutions with multiple `.csproj` files.

**Complement with Dependabot** for automated PR-based updates:
```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "npm"
    directory: "/frontend"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10
  - package-ecosystem: "nuget"
    directory: "/backend"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10
```

Also enable NuGet audit in `.csproj` to catch vulnerabilities at build time locally:
```xml
<PropertyGroup>
    <NuGetAudit>true</NuGetAudit>
    <NuGetAuditMode>all</NuGetAuditMode>
    <NuGetAuditLevel>low</NuGetAuditLevel>
    <TreatWarningsAsErrors>true</TreatWarningsAsErrors>
</PropertyGroup>
```

### Job 3: Secrets Scanning with Gitleaks

`fetch-depth: 0` is critical — scans the entire git history, not just the latest commit. A secret committed 6 months ago and "deleted" in a subsequent commit is still in history.

**Pre-commit hook to catch secrets before they reach CI:**
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.0
    hooks:
      - id: gitleaks
```

Install pre-commit: `pip install pre-commit && pre-commit install`

**Custom Gitleaks rules** for organization-specific patterns:
```toml
# .gitleaks.toml
[[rules]]
  id = "azure-connection-string"
  description = "Azure Storage Connection String"
  regex = '''DefaultEndpointsProtocol=https;AccountName=[^;]+;AccountKey=[A-Za-z0-9+/=]{88}'''
  tags = ["azure", "storage"]
```

### Job 4: Container Scanning with Trivy

Two scan modes:

**Filesystem scan** (`scan-type: fs`) — scans the repository for vulnerable packages declared in `package-lock.json`, `packages.lock.json`, etc. Runs without building the image, so it catches issues early.

**Image scan** — scans the built container image including OS packages. This catches vulnerabilities in the base image that aren't visible in dependency files.

**Container security best practices enforced by Trivy scanning:**

```dockerfile
# Use distroless (no shell, no package manager — minimal attack surface)
FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS base

# Run as non-root user
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser

# Read-only filesystem (use volume mounts for writable paths)
# Enforced at pod level: readOnlyRootFilesystem: true

# No SUID/SGID binaries
RUN find / -perm /6000 -type f -exec chmod a-s {} \; 2>/dev/null || true
```

**Trivy Operator** for continuous in-cluster scanning (deploy separately):
```bash
helm install trivy-operator aquasecurity/trivy-operator \
  --namespace trivy-system \
  --create-namespace \
  --set="trivy.ignoreUnfixed=true"
```

### Job 5: IaC Scanning with Checkov

Checkov covers 1000+ built-in policies for CIS benchmarks, HIPAA, PCI-DSS, and SOC2 across:
- Terraform (Azure provider)
- Bicep / ARM templates
- Kubernetes YAML manifests
- Dockerfile
- GitHub Actions workflows

`soft_fail: false` makes the job fail on policy violations. Use `check` / `skip-check` for exceptions:

```yaml
- uses: bridgecrewio/checkov-action@master
  with:
    directory: infra/
    framework: terraform
    soft_fail: false
    skip-check: >
      CKV_AZURE_88,
      CKV2_AZURE_21
```

Document every skipped check with justification in a comment or separate file. Unapproved exceptions require a security review.

---
