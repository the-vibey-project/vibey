---
id: skill-mutation-testing-1ec2aedb26
purpose: mutation testing
source: src/vibey_tools/skills/plugins/quality-engineering/skills/python-quality-testing/SKILL.md
requires: ["skill-property-based-testing-with-hypothesis-34767fbc51"]
links: ["skill-static-analysis-the-ruff-led-stack-0ac1d5e4c5"]
---

## Mutation Testing

Mutation testing validates your test suite by introducing code mutations and checking whether your tests catch them.

**Mutation score = (killed mutants / total non-equivalent mutants) × 100**

A mutation score below 60% indicates a weak test suite regardless of coverage percentage.

### mutmut (Simplest)

```bash
# Install
pip install mutmut

# Run on a specific module
mutmut run --paths-to-mutate src/myapp/orders.py

# View results
mutmut results
mutmut show 5  # show specific surviving mutant

# HTML report
mutmut html
```

### cosmic-ray (More Configurable)

```toml
# cosmic-ray.toml
[cosmic-ray]
module-path = "src/myapp/orders.py"
timeout = 10.0

[cosmic-ray.distributor]
name = "local"

[[cosmic-ray.interceptors]]
name = "pragma"  # skip # pragma: no mutate lines
```

```bash
cosmic-ray init cosmic-ray.toml session.sqlite
cosmic-ray exec cosmic-ray.toml session.sqlite
cosmic-ray report session.sqlite
```

### Mutation Testing as an Audit Tool
Run mutation testing **as an audit, not a CI gate**. Running on every commit is too slow. Use it:
- Before a major release to validate critical module test quality
- When onboarding a new module to establish a baseline
- When investigating why a bug escaped your test suite

Target 80%+ mutation score for business-critical code.

---
