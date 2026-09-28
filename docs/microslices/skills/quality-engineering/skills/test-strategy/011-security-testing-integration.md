---
id: skill-security-testing-integration-a3cc83ba37
purpose: security testing integration
source: src/vibey_tools/skills/plugins/quality-engineering/skills/test-strategy/SKILL.md
requires: ["skill-performance-testing-strategy-5501763d28"]
links: ["skill-assessing-test-suite-health-diagnostic-questions-2047556988"]
---

## Security Testing Integration

Security testing should be distributed across all layers, not isolated to a pentest phase:

| Layer | Security Test Type | Tool | Timing |
|---|---|---|---|
| **Static analysis** | SAST (source code vulnerabilities) | Bandit, Semgrep | Every PR |
| **Unit** | Input validation logic | pytest with adversarial inputs | Every PR |
| **Integration** | Auth enforcement, SQL injection | pytest with malicious payloads | Every PR |
| **Contract** | API security headers, auth requirements | Pact with security scenarios | Every PR |
| **E2E** | DAST (runtime vulnerability scanning) | OWASP ZAP baseline | Every build |
| **Pentest** | Manual exploitation, business logic | Internal quarterly, external annually | Scheduled |

**OWASP ZAP baseline scan in CI:**
```yaml
- task: CmdLine@2
  displayName: 'OWASP ZAP Baseline Scan'
  inputs:
    script: |
      docker run -t owasp/zap2docker-stable zap-baseline.py \
        -t https://staging.myapp.com \
        -J zap-report.json \
        -x zap-report.xml
```

The baseline scan catches common vulnerabilities (missing security headers, information disclosure) automatically. It will not catch business logic vulnerabilities or complex authentication bypass — that requires human testing.

---
