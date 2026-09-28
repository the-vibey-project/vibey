---
id: skill-smurf-evaluating-test-portfolio-health-e5e2ac8235
purpose: smurf evaluating test portfolio health
source: src/vibey_tools/skills/plugins/quality-engineering/skills/python-quality-testing/SKILL.md
requires: ["skill-test-shape-models-choosing-the-right-distribution-8c550ebcea"]
links: ["skill-iso-iec-25010-2023-quality-characteristics-1d07042353"]
---

## SMURF: Evaluating Test Portfolio Health

Google's SMURF framework (October 2024, Google Testing Blog) evaluates tests across five dimensions:

| Dimension | What It Measures | Good Sign | Bad Sign |
|---|---|---|---|
| **Speed** | How fast tests execute | Unit suite < 5 min; integration < 15 min | Any slow test blocking CI |
| **Maintainability** | Ease of understanding and updating | Tests read like documentation | Tests require context to understand |
| **Utilization** | Frequency tests are actually run | All tests run on every PR | Tests only run on main branch |
| **Reliability** | Consistency of results | < 2% flake rate per test | Retries needed to pass |
| **Fidelity** | How closely tests simulate real usage | Integration tests use real data formats | Tests mock everything away |

Run a SMURF audit quarterly. Each dimension can degrade independently.

---
