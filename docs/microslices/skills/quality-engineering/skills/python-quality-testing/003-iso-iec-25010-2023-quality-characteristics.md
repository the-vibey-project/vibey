---
id: skill-iso-iec-25010-2023-quality-characteristics-1d07042353
purpose: iso iec 25010 2023 quality characteristics
source: src/vibey_tools/skills/plugins/quality-engineering/skills/python-quality-testing/SKILL.md
requires: ["skill-smurf-evaluating-test-portfolio-health-e5e2ac8235"]
links: ["skill-black-box-test-design-techniques-1d068a0615"]
---

## ISO/IEC 25010:2023 Quality Characteristics

The 2023 revision of the SQuaRE standard (ISO/IEC 25010) expanded from 8 to **9 product quality characteristics**. Testing strategy should cover all relevant characteristics:

| Characteristic | What It Covers | Test Approach |
|---|---|---|
| **Functional Suitability** | Completeness, correctness, appropriateness | Acceptance tests, BDD scenarios |
| **Performance Efficiency** | Time behavior, resource usage, capacity | Load testing (Locust), profiling |
| **Compatibility** | Co-existence, interoperability | Integration tests, contract tests |
| **Interaction Capability** | Usability (renamed from Usability) | UI tests, accessibility checks |
| **Reliability** | Maturity, availability, fault tolerance | Chaos engineering, FDRT measurement |
| **Security** | Confidentiality, integrity, authentication | SAST (Bandit), DAST, pen testing |
| **Maintainability** | Modularity, analyzability, testability | Mutation testing, cyclomatic complexity |
| **Flexibility** | Adaptability (renamed from Portability) | Multi-environment tests, testcontainers |
| **Safety** | *(new in 2023)* — operational constraint | Fault injection, boundary condition tests |

---
