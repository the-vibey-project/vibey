---
id: skill-business-function-3-implementation-29f089687d
purpose: business function 3 implementation
source: src/vibey_tools/skills/plugins/compliance-frameworks/skills/owasp-samm/SKILL.md
requires: ["skill-business-function-2-design-cf53d1a630"]
links: ["skill-business-function-4-verification-b5146729bb"]
---

## Business Function 3: Implementation

### Practice I1: Secure Build
Integrate security into the build and CI/CD pipeline.

**Level 1:** Basic dependency management (know what third-party libraries you use). Some developers use linters. Source control in use for all code.

**Level 2:** Static Application Security Testing (SAST) integrated into CI pipeline. Software Composition Analysis (SCA) for third-party dependency vulnerabilities. Build fails (or alerts) on high-severity findings. Secrets scanning active (no hardcoded credentials).

**Level 3:** SAST, SCA, secrets scanning, and IaC security scanning all integrated and blocking on critical/high. Developers receive actionable security findings at commit time. Security findings tracked and measured over time. Build pipeline itself is secured and audited.

**Key tools:**
- SAST: Semgrep, SonarQube, CodeQL, Checkmarx, Snyk Code
- SCA: Snyk, OWASP Dependency-Check, Dependabot, JFrog Xray
- Secrets: GitGuardian, TruffleHog, detect-secrets
- IaC: Checkov, tfsec, KICS, Terrascan

### Practice I2: Secure Deployment
Harden deployment processes and infrastructure configurations.

**Level 1:** Environment separation (dev/staging/prod). No production secrets in source code. Basic change management for production deployments.

**Level 2:** Infrastructure as Code (IaC) with security configuration checks. Container image scanning before deployment. Deployment approvals required for production. Environment configurations audited against CIS Benchmarks.

**Level 3:** Immutable infrastructure. All deployments via automated, audited pipeline. Runtime security monitoring (CWPP, Falco). Zero-trust network architecture. Automated drift detection and remediation.

### Practice I3: Defect Management
Track, prioritize, and remediate security defects systematically.

**Level 1:** Security bugs tracked in the same system as functional bugs. Critical security vulnerabilities are prioritized above feature work.

**Level 2:** Security defect SLAs defined by severity (Critical: 24h; High: 7 days; Medium: 30 days; Low: 90 days). Security backlog visible to engineering leadership. Trend metrics tracked (are we finding and fixing more over time?).

**Level 3:** Automated vulnerability management workflow (scanner finds → ticket created → assigned → tracked to closure). Root cause analysis for recurring vulnerability classes. Vulnerability density metrics by team and application.


---
