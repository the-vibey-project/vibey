---
id: skill-pytest-the-complete-reference-dd27bcd55e
purpose: pytest the complete reference
source: src/vibey_tools/skills/plugins/quality-engineering/skills/python-quality-testing/SKILL.md
requires: ["skill-black-box-test-design-techniques-1d068a0615"]
links: ["skill-tdd-red-green-refactor-72bf781e1e"]
---

## pytest: The Complete Reference

pytest 9.x (requires Python ≥ 3.10) is the de facto Python testing standard.

### Fixtures

```python
# conftest.py — shared fixtures, auto-discovered by pytest
import pytest
from sqlalchemy import create_engine
from myapp.db import Base

@pytest.fixture(scope="session")
def db_engine():
    """Session-scoped: one engine for entire test run."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)

@pytest.fixture(scope="function")  # default scope
def db_session(db_engine):
    """Function-scoped: rolls back after each test."""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def user_factory(db_session):
    """Factory fixture: returns a callable."""
    def _make_user(**kwargs):
        defaults = {"email": "test@example.com", "role": "user"}
        user = User(**{**defaults, **kwargs})
        db_session.add(user)
        db_session.flush()
        return user
    return _make_user
```

**Fixture scopes:** `function` (default), `class`, `module`, `package`, `session`. Use `session` scope for expensive setup (database containers, HTTP clients). Use `function` scope for anything with mutable state.

### Parametrize (Cartesian Products)

```python
@pytest.mark.parametrize("user_role", ["admin", "editor", "viewer"])
@pytest.mark.parametrize("resource_type", ["document", "report", "dashboard"])
def test_access_control(user_role, resource_type, permission_service):
    # Creates 3 × 3 = 9 test cases automatically
    result = permission_service.can_access(user_role, resource_type)
    assert isinstance(result, bool)
```

### conftest.py Hierarchy

```
project/
├── conftest.py           # project-wide fixtures
├── tests/
│   ├── conftest.py       # test-directory-wide fixtures
│   ├── unit/
│   │   ├── conftest.py   # unit-test-specific fixtures
│   │   └── test_*.py
│   └── integration/
│       ├── conftest.py   # integration-test-specific fixtures
│       └── test_*.py
```

### Marks (Built-in and Custom)

```python
# Built-in marks
@pytest.mark.skip(reason="Known flake, tracked in JIRA-123")
@pytest.mark.xfail(reason="Bug in upstream library, expected failure")
@pytest.mark.slow  # custom mark

# pytest.ini or pyproject.toml — register custom marks
[tool.pytest.ini_options]
markers = [
    "slow: marks tests as slow (deselect with '-m not slow')",
    "integration: marks tests requiring external services",
    "smoke: marks critical path smoke tests",
]

# Run only smoke tests in CI
# pytest -m smoke
# Run everything except slow tests locally
# pytest -m "not slow"
```

### Coverage with pytest-cov

```toml
# pyproject.toml
[tool.coverage.run]
source = ["src"]
branch = true          # always enable branch coverage
omit = ["*/migrations/*", "*/tests/*"]

[tool.coverage.report]
fail_under = 80
show_missing = true
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "@overload",
]
```

```bash
# Run tests with coverage
pytest --cov=src --cov-report=xml --cov-report=term-missing --cov-fail-under=80
```

**Branch coverage uncovers ~25% more untested paths than line coverage.** Always enable it. Use coverage as a **floor**, not a goal — 100% coverage targets are gamed. Target: overall ≥ 80%, critical paths (auth, data access, payments) ≥ 100%.

---
