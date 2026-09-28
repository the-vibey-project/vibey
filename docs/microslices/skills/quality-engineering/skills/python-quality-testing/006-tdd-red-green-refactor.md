---
id: skill-tdd-red-green-refactor-72bf781e1e
purpose: tdd red green refactor
source: src/vibey_tools/skills/plugins/quality-engineering/skills/python-quality-testing/SKILL.md
requires: ["skill-pytest-the-complete-reference-dd27bcd55e"]
links: ["skill-bdd-with-pytest-bdd-df49ce9f51"]
---

## TDD: Red-Green-Refactor

Kent Beck's Test-Driven Development cycle applied in Python:

1. **Red** — write a failing test that expresses the desired behavior (the test should fail because the feature doesn't exist yet)
2. **Green** — write the minimum code needed to make the test pass (no more)
3. **Refactor** — improve the code's structure without changing its behavior (tests must still pass)

### London School vs. Chicago School

| | London School (Mockist) | Chicago School (Classicist) |
|---|---|---|
| **Focus** | Test object in complete isolation | Test behavior of a cluster of objects |
| **Approach** | Mock all collaborators | Use real objects; mock only I/O boundaries |
| **When to use** | Legacy code with unclear boundaries | New code with well-defined boundaries |
| **Risk** | Over-mocking couples tests to implementation | Integration issues found later |
| **Reference** | *GOOS* (Freeman & Pryce, 2009) | Kent Beck *TDD by Example* |

**Practical guidance:** Prefer Chicago school (real objects, mock only I/O) for new code. Mock only at infrastructure boundaries: HTTP clients, database sessions, file I/O, time, external APIs.

### autospec: The Gold Standard for Mocking

```python
from unittest.mock import patch, create_autospec
from myapp.services import EmailService, UserService

# BAD: bare Mock doesn't validate method signatures
with patch.object(EmailService, 'send') as mock_send:
    mock_send.return_value = True
    # This won't fail even if send() signature changes

# GOOD: autospec validates signatures match real object
with patch.object(EmailService, 'send', autospec=True) as mock_send:
    mock_send.return_value = True
    # This WILL fail if send() signature changes in EmailService
```

**Always prefer `autospec=True`.** It ensures mock signatures match real objects, catching API drift.

**Patching rule:** Patch where the object is **looked up**, not where it is **defined**.
```python
# myapp/orders.py imports and uses: from myapp.services import EmailService
# Correct patch location:
with patch('myapp.orders.EmailService'):  # where it's used
    pass
# NOT: patch('myapp.services.EmailService')  # where it's defined
```

---
