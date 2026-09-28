---
id: skill-sprs-score-system-2a42f8675e
purpose: sprs score system
source: src/vibey_tools/skills/plugins/compliance-frameworks/skills/nist-800-171/SKILL.md
requires: ["skill-the-14-control-families-ad18b18d3c"]
links: ["skill-self-assessment-methodology-8c70848f7c"]
---

## SPRS Score System

The **Supplier Performance Risk System (SPRS)** score represents a contractor's self-assessed compliance posture. DoD contractors must submit scores via SPRS before award and maintain them.

**Scoring methodology (DoD Assessment Methodology v1.2.1):**
- Maximum score: **110** (full compliance)
- Each of the 110 controls has a point value (most are 1 point; some multi-part controls are worth more)
- Start at 110; deduct points for each unmet control
- Negative scores are possible and reportable
- Formula: `SPRS Score = 110 - (sum of deductions for non-compliant controls)`

**Point deduction values:**
- 1-point controls: most basic controls
- 3-point controls: high-impact controls (MFA, encryption, audit logging, boundary protection)
- 5-point controls: critical controls (SSP, incident response capability)

**SPRS submission requirements:**
- Submit at: https://www.sprs.csd.disa.mil
- Required before contract award (DFARS 252.204-7019)
- Must reflect current state at time of submission
- DoD can request the supporting SSP for verification (DFARS 252.204-7020)


---
