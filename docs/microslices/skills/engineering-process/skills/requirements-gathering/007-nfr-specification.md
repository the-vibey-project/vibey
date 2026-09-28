---
id: skill-nfr-specification-e5c6c10682
purpose: nfr specification
source: src/vibey_tools/skills/plugins/engineering-process/skills/requirements-gathering/SKILL.md
requires: ["skill-prioritization-frameworks-b02a8af4b7"]
links: ["skill-validation-and-analysis-cc33d7c0fa"]
---

## NFR Specification

### Quality Attribute Taxonomy
Performance, scalability, availability, reliability, security, maintainability, usability/accessibility, testability, observability, deployability, portability.

### Planguage (Tom Gilb) — Gold Standard for Testable NFRs
Keywords:
- **Scale**: unit of measure
- **Meter**: how to measure
- **Past**: benchmark value
- **Goal/Must**: target/constraint levels
- **Wish**: aspirational level
- **Fit Criterion**: numeric pass/fail condition

**Key lesson**: practitioners struggle to define scales of measure and practical meters; unrealistic quantification can cause delay. Quantify against real business need.

### Key NFR Benchmarks
- Availability SLAs: 99.9% ≈ 8.76 hrs/yr downtime; 99.99% ≈ 52.6 min/yr.
- Specify with RTO/RPO for availability/reliability.
- Security: authN/authZ, data classification, encryption at rest/in transit, audit logging, compliance frameworks (SOC2/PCI-DSS/HIPAA/GDPR).
- Usability/accessibility: **WCAG 2.1 AA** is the baseline.
- Ban adjective-requirements: "fast" and "user-friendly" are not requirements.

### Quality-Attribute Scenarios (Bass/Clements/Kazman)
For architecture-impactful requirements: **source–stimulus–environment–artifact–response–response measure**.

---
