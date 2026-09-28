---
id: skill-part-11-phase-7-devsecops-pipeline-installation-44f0bad30e
purpose: part 11 phase 7 devsecops pipeline installation
source: src/vibey_tools/skills/plugins/security-first-dev/skills/codebase-modernization/SKILL.md
requires: ["skill-part-10-phase-6-logging-and-observability-823177b59f"]
links: ["skill-part-12-phase-8-infrastructure-modernization-fcc20a52d3"]
---

## PART 11: PHASE 7 — DEVSECOPS PIPELINE INSTALLATION

Install the pipeline on every repository, even before other phases are complete. A pipeline
that catches some issues on day one is better than a perfect pipeline on day ninety.

### 11.1 Minimal Viable Security Pipeline (Install First)

```yaml
# .github/workflows/security.yml
name: Security Gates
on:
  push: { branches: [main, develop] }
  pull_request: { branches: [main] }
permissions:
  security-events: write
  contents: read

jobs:
  secrets-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }  # full history required for Gitleaks
      - uses: gitleaks/gitleaks-action@v2
        env: { GITHUB_TOKEN: '${{ secrets.GITHUB_TOKEN }}' }

  sast-semgrep:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: returntocorp/semgrep-action@v1
        with:
          config: 'p/secrets p/owasp-top-ten p/csharp p/typescript'
          generateSarif: true
      - uses: github/codeql-action/upload-sarif@v3
        with: { sarif_file: semgrep.sarif }
        if: always()
```

### 11.2 Adding Gates Progressively (One Job Per Sprint)

```yaml
# Sprint 2 — add when dependency audit is clean enough to gate on
  sca:
    uses: snyk/actions/dotnet@master
    with: { args: '--severity-threshold=high' }

# Sprint 2 — add when Docker images are in use
  container-scan:
    if: hashFiles('Dockerfile') != ''
    # trivy CRITICAL,HIGH exit-code 1

# Sprint 3 — add when IaC exists
  iac-scan:
    if: hashFiles('infra/**/*.bicep') != ''
    # checkov bicep soft_fail false

# Sprint 3 — add when coverage gate is established
  build-and-test:
    # dotnet test with coverage threshold
```

### 11.3 Pre-Commit Hook

```bash
pip install pre-commit
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.0
    hooks: [{ id: gitleaks }]
  - repo: https://github.com/returntocorp/semgrep
    rev: v1.45.0
    hooks:
      - id: semgrep
        args: ['--config', 'p/secrets', '--config', 'p/owasp-top-ten', '--error']
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks: [{ id: detect-private-key }, { id: detect-aws-credentials }]

# Each developer runs once after cloning:
pre-commit install
```

---
