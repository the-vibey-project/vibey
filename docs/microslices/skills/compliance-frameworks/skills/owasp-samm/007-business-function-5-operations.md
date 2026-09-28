---
id: skill-business-function-5-operations-4b93a3d6a8
purpose: business function 5 operations
source: src/vibey_tools/skills/plugins/compliance-frameworks/skills/owasp-samm/SKILL.md
requires: ["skill-business-function-4-verification-b5146729bb"]
links: ["skill-assessment-methodology-93648ccda6"]
---

## Business Function 5: Operations

### Practice O1: Incident Management
Detect, respond to, and learn from security incidents in production.

**Level 1:** Incident response plan exists. Security events logged. Basic alerting for obvious attacks (failed logins, malware alerts). On-call process includes security escalation path.

**Level 2:** SIEM with tuned detection rules. IR runbooks for common incident types. Post-incident reviews conducted. Incident metrics tracked (MTTD, MTTR). Security team notified within defined SLA.

**Level 3:** Advanced threat detection (UEBA, behavioral analytics). Purple team exercises to validate detection capability. Automated response playbooks (SOAR). Threat intelligence integration. Regular IR drills and red team exercises.

### Practice O2: Environment Management
Maintain secure configurations across all environments throughout the software lifecycle.

**Level 1:** Hardened base images for servers and containers. Basic configuration management (manual or scripted). Known default credentials changed.

**Level 2:** CIS Benchmark compliance for all infrastructure. Configuration drift detection (Chef InSpec, AWS Config, Azure Policy). Automated patching or patch tracking with SLAs. Vulnerability scanning of production infrastructure.

**Level 3:** Policy-as-code enforcement across all environments. Immutable infrastructure eliminates configuration drift. Continuous compliance monitoring with automated remediation. Cloud security posture management (CSPM) tools deployed.

### Practice O3: Operational Management
Integrate security into operational processes: change management, access management, data management.

**Level 1:** Access reviews conducted periodically. Sensitive data locations identified. Basic data retention policy.

**Level 2:** Privileged access management (PAM). Data classification applied to production data. Operational runbooks include security considerations. Vendor access reviewed and limited.

**Level 3:** Just-in-time privileged access. Automated data discovery and classification. Security integrated into all operational runbooks. Supply chain security practices (software bill of materials, SBOM). Operational security KPIs measured and reported.


---
