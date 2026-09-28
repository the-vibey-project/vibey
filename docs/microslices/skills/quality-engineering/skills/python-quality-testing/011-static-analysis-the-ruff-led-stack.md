---
id: skill-static-analysis-the-ruff-led-stack-0ac1d5e4c5
purpose: static analysis the ruff led stack
source: src/vibey_tools/skills/plugins/quality-engineering/skills/python-quality-testing/SKILL.md
requires: ["skill-mutation-testing-1ec2aedb26"]
links: ["skill-azure-cloud-native-testing-2e886e185f"]
---

## Static Analysis: The Ruff-Led Stack

### Ruff (Replaces Flake8 + Black + isort + pyupgrade + dozens of plugins)

Ruff (Astral) is **10–100× faster** than Flake8, written in Rust. It reimplements 800+ rules from Flake8, pycodestyle, isort, pydocstyle, and more. Adopted by FastAPI, Pandas, Airflow, SciPy, and Pydantic.

```toml
# pyproject.toml
[tool.ruff]
target-version = "py311"
line-length = 88

[tool.ruff.lint]
select = [
    "E",     # pycodestyle errors
    "F",     # pyflakes
    "I",     # isort
    "N",     # pep8-naming
    "UP",    # pyupgrade
    "S",     # bandit (security)
    "B",     # bugbear
    "C4",    # flake8-comprehensions
    "SIM",   # flake8-simplify
    "TCH",   # type-checking imports
]
ignore = ["E501"]  # line length handled by formatter

[tool.ruff.format]
quote-style = "double"

[tool.ruff.lint.isort]
known-first-party = ["myapp"]
```

```bash
ruff check .              # lint
ruff check . --fix        # auto-fix safe issues
ruff format .             # format (Black-compatible)
ruff format . --check     # check formatting without modifying
```

### mypy (Strict Mode)

```toml
# pyproject.toml
[tool.mypy]
python_version = "3.11"
strict = true
# Strict mode enables:
# disallow_untyped_defs = true
# disallow_any_generics = true
# warn_return_any = true
# warn_unused_ignores = true
# no_implicit_reexport = true
# strict_equality = true

[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false  # relax for tests
```

**Protocol for structural typing** (preferred over ABC in most cases):

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Repository(Protocol):
    def get(self, id: str) -> dict | None: ...
    def save(self, entity: dict) -> str: ...
    def delete(self, id: str) -> None: ...

# Works with any object that has get/save/delete methods
# No inheritance required — duck typing with type safety
```

---
