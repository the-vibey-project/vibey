---
id: skill-business-function-4-verification-b5146729bb
purpose: business function 4 verification
source: src/vibey_tools/skills/plugins/compliance-frameworks/skills/owasp-samm/SKILL.md
requires: ["skill-business-function-3-implementation-29f089687d"]
links: ["skill-business-function-5-operations-4b93a3d6a8"]
---

## Business Function 4: Verification

### Practice V1: Architecture Assessment
Verify that application architecture meets security requirements and threat model findings.

**Level 1:** Informal security review of major new systems or significant architecture changes. Checklist-based: authentication handled correctly? Authorization enforced? Sensitive data encrypted?

**Level 2:** Formal architecture review process with documented findings and sign-off. Security architect involvement in design reviews. Architecture review aligned to threat model.

**Level 3:** Continuous architecture review integrated with change management. Automated architecture compliance checking (e.g., policy-as-code for cloud infrastructure). Findings fed back into design standards.

### Practice V2: Requirements-Driven Testing
Test security requirements, not just functionality.

**Level 1:** Pen tester or security team reviews the application for OWASP Top 10 vulnerabilities. Security test cases exist for authentication and authorization.

**Level 2:** Security test cases written from security requirements and threat model. Security testing integrated into QA process. DAST (Dynamic Application Security Testing) running against staging environments.

**Level 3:** Comprehensive security test suite covering OWASP ASVS verification requirements. Security regression tests prevent re-introduction of fixed vulnerabilities. Fuzz testing for critical input handlers.

**Key tools:**
- DAST: OWASP ZAP, Burp Suite, Invicti, Detectify
- API testing: Postman with security tests, OWASP ZAP API scan
- Fuzz testing: AFL++, libFuzzer, RESTler

### Practice V3: Security Testing
Conduct dedicated security testing beyond functional testing.

**Level 1:** Annual penetration test by internal team or third party. OWASP Top 10 coverage. Critical findings remediated before next release.

**Level 2:** Annual external penetration test + ongoing internal testing. Bug bounty or vulnerability disclosure program considered. Pre-release security reviews for major features. DAST running continuously against staging.

**Level 3:** Continuous automated security testing in CI/CD (SAST + DAST + SCA). Regular penetration tests with retesting of remediated findings. Bug bounty program active. Red team exercises for critical systems. Security chaos engineering.

---
