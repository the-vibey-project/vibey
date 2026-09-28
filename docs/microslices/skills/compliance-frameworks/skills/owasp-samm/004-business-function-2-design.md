---
id: skill-business-function-2-design-cf53d1a630
purpose: business function 2 design
source: src/vibey_tools/skills/plugins/compliance-frameworks/skills/owasp-samm/SKILL.md
requires: ["skill-business-function-1-governance-1ec3586e42"]
links: ["skill-business-function-3-implementation-29f089687d"]
---

## Business Function 2: Design

### Practice D1: Threat Assessment
Identify threats to applications and systems as part of the design process.

**Level 1:** Ad hoc threat identification for high-risk features. At least a basic question list: "What could go wrong? Who might attack this? What data is sensitive?"

**Level 2:** Structured threat modeling process (STRIDE, PASTA, or attack tree) for all new features and significant changes. Threats documented and linked to security requirements. Threat models reviewed by security team.

**Level 3:** Threat modeling is fully integrated into design sprints. Automated tooling assists (e.g., OWASP Threat Dragon, Microsoft TMT). Historical threat data feeds future models. Risk-ranked threat catalog maintained.

### Practice D2: Security Requirements
Define and track security requirements as a first-class concern in feature development.

**Level 1:** Security requirements exist for the most critical features (authentication, authorization, encryption). Checked manually during code review.

**Level 2:** Security requirements library aligned to OWASP ASVS or internal standards. Requirements attached to user stories in sprint backlog. Definition of Done includes security requirement sign-off.

**Level 3:** Automated requirements traceability. Security requirements derived from threat models and compliance obligations. Metrics on requirement coverage and fulfillment.

### Practice D3: Security Architecture
Design systems with security as a structural concern, not an add-on.

**Level 1:** Security architecture principles documented (e.g., least privilege, defense in depth, input validation, fail securely). Applied informally.

**Level 2:** Reference architectures for common patterns (authentication, API security, data storage, microservices). Architecture review for new systems and significant changes. Security architects involved in design decisions.

**Level 3:** Security architecture governance process. Architecture decisions recorded (ADRs). Reusable security components and libraries provided to developers. Continuous architecture review as systems evolve.

---
