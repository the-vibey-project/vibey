---
id: skill-starting-points-by-organization-type-8ddb889951
purpose: starting points by organization type
source: src/vibey_tools/skills/plugins/compliance-frameworks/skills/owasp-samm/SKILL.md
requires: ["skill-samm-score-reference-15-practices-summary-table-0512e58c16"]
links: ["skill-security-champions-program-g3-level-2-4bfd7b902f"]
---

## Starting Points by Organization Type

### Startup (< 50 engineers, pre-SOC2/compliance pressure)
**Realistic starting score:** 0.2–0.5 across most practices

**Priority Level 1 quick wins (do these first):**
1. G3 — Security awareness training: 1-hour OWASP Top 10 session for all developers
2. I1 — Secure build: Add Dependabot/Snyk to GitHub repos; add secrets scanning
3. I3 — Defect management: Create a security label in Jira; agree on severity SLAs
4. O1 — Incident management: Write a 1-page IRP; know who to call when something goes wrong
5. V3 — Security testing: Schedule one annual pen test

**6-month target score:** 1.0 across most practices

### Growing SaaS (50–200 engineers, SOC2 in progress or complete)
**Realistic starting score:** 0.8–1.2

**Priority Level 2 improvements:**
1. G2 — Policy and compliance: Full policy set; annual review cycle
2. D1 — Threat assessment: Introduce threat modeling for all significant new features
3. I1 — Secure build: SAST and SCA integrated into CI pipeline with blocking on critical
4. V3 — Security testing: DAST running against staging; annual pen test with retest
5. O2 — Environment management: CIS Benchmark compliance for cloud infrastructure

**12-month target score:** 1.5 across most practices; 2.0 in highest-risk areas

### Enterprise (200+ engineers, mature DevSecOps, regulated industry)
**Realistic starting score:** 1.5–2.0

**Priority Level 3 improvements:**
1. I1 — Secure build: All security gates in pipeline; findings tracked and measured
2. V3 — Security testing: Bug bounty or continuous pen testing; red team exercises
3. O1 — Incident management: SOAR automation; MTTD/MTTR measured and improving
4. D1 — Threat assessment: Automated threat modeling tooling; historical threat catalog
5. G1 — Strategy & metrics: Security metrics in executive dashboards; OKRs for security


---
