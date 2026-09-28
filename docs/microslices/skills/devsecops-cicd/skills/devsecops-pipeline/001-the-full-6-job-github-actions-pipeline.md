---
id: skill-the-full-6-job-github-actions-pipeline-b6e5ccb08a
purpose: the full 6 job github actions pipeline
source: src/vibey_tools/skills/plugins/devsecops-cicd/skills/devsecops-pipeline/SKILL.md
requires: []
links: ["skill-job-by-job-breakdown-a1bcf6b459"]
---

## The Full 6-Job GitHub Actions Pipeline

The complete DevSecOps pipeline integrates SAST, SCA, secrets scanning, container scanning, IaC scanning, and a deploy job that only runs if all security gates pass.

```yaml
# .github/workflows/devsecops.yml
name: DevSecOps Pipeline
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  security-events: write
  contents: read
  id-token: write    # Required for OIDC Azure auth in deploy job

jobs:
  # ── JOB 1: SAST — Static Application Security Testing ──────────────────────
  sast-semgrep:
    name: SAST (Semgrep)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: returntocorp/semgrep-action@v1
        with:
          config: 'p/security-audit p/owasp-top-ten p/csharp p/typescript p/secrets'
          generateSarif: true
      - uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: semgrep.sarif
        if: always()

  sast-codeql:
    name: SAST (CodeQL)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: github/codeql-action/init@v3
        with:
          languages: 'csharp, javascript'   # CodeQL excels at C# and TypeScript
          queries: security-extended
      - uses: github/codeql-action/autobuild@v3
      - uses: github/codeql-action/analyze@v3
        with:
          output: codeql-results.sarif
      - uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: codeql-results.sarif
        if: always()

  # ── JOB 2: SCA — Software Composition Analysis (dependencies) ─────────────
  sca-snyk:
    name: SCA (Snyk)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Snyk for .NET
        uses: snyk/actions/dotnet@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          args: '--severity-threshold=high --all-projects'
      - name: Run Snyk for Node
        uses: snyk/actions/node@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          args: '--severity-threshold=high'

  # ── JOB 3: Secrets Scanning ─────────────────────────────────────────────────
  secrets-scan:
    name: Secrets Scan (Gitleaks)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0    # Full history — scan all commits, not just latest
      - uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GITLEAKS_LICENSE: ${{ secrets.GITLEAKS_LICENSE }}   # Required for org scans

  # ── JOB 4: Container Scanning ───────────────────────────────────────────────
  container-scan:
    name: Container Scan (Trivy)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build image
        run: docker build -t myapp:${{ github.sha }} .
      - name: Scan filesystem (catches IaC and deps in repo)
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          severity: 'CRITICAL,HIGH'
          exit-code: '1'
          format: sarif
          output: trivy-fs.sarif
      - name: Scan container image
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'myapp:${{ github.sha }}'
          severity: 'CRITICAL,HIGH'
          exit-code: '1'
          format: sarif
          output: trivy-image.sarif
      - uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: trivy-image.sarif
        if: always()

  # ── JOB 5: IaC Scanning ─────────────────────────────────────────────────────
  iac-scan:
    name: IaC Scan (Checkov)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Checkov for Terraform
        uses: bridgecrewio/checkov-action@master
        with:
          directory: infra/
          framework: terraform
          soft_fail: false
          output_format: sarif
          output_file_path: checkov-tf.sarif
      - name: Checkov for Bicep
        uses: bridgecrewio/checkov-action@master
        with:
          directory: infra/
          framework: bicep
          soft_fail: false
      - uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: checkov-tf.sarif
        if: always()

  # ── JOB 6: Deploy — Only if ALL security gates pass ─────────────────────────
  deploy:
    name: Deploy to Production
    needs: [sast-semgrep, sast-codeql, sca-snyk, secrets-scan, container-scan, iac-scan]
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest
    environment: production    # Requires environment protection rules
    steps:
      - uses: actions/checkout@v4
      - name: Azure Login (OIDC — no stored secrets)
        uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
      - name: Deploy
        run: |
          echo "All ${{ needs.sast-semgrep.result }}, ${{ needs.sca-snyk.result }} security gates passed — deploying"
          # az deployment group create ...
```

---
