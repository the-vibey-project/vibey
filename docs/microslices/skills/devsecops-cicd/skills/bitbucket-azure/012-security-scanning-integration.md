---
id: skill-security-scanning-integration-3b88587eb7
purpose: security scanning integration
source: src/vibey_tools/skills/plugins/devsecops-cicd/skills/bitbucket-azure/SKILL.md
requires: ["skill-known-limitations-and-gotchas-eea0d53e7f"]
links: ["skill-recommendations-by-team-profile-36d40bd4e5"]
---

## Security Scanning Integration

Bitbucket has no first-party security scanning comparable to Dependabot or CodeQL. Wire in third-party tools via pipes:

```yaml
pipelines:
  pull-requests:
    '**':
      - parallel:
          steps:
            - step:
                name: Snyk Dependency Scan
                script:
                  - pipe: snyk/snyk-scan:1.0.0
                    variables:
                      SNYK_TOKEN: $SNYK_TOKEN
                      SEVERITY_THRESHOLD: high
                      FAIL_ON_ISSUES: 'true'

            - step:
                name: Secrets Scan
                script:
                  - pip install gitleaks
                  - gitleaks detect --source . --verbose

            - step:
                name: SonarCloud Analysis
                script:
                  - pipe: sonarsource/sonarcloud-scan:2.0.0
                    variables:
                      SONAR_TOKEN: $SONAR_TOKEN
```

For a comprehensive DevSecOps posture on Bitbucket, the pipeline cannot match GitHub Actions' first-party toolchain (Dependabot + CodeQL + secret scanning built into the platform). Budget for Snyk or Mend licenses as equivalents.

---
