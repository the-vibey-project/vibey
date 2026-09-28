---
id: skill-test-data-management-fa76c76ab6
purpose: test data management
source: src/vibey_tools/skills/plugins/quality-engineering/skills/test-strategy/SKILL.md
requires: ["skill-anti-patterns-1327788ce4"]
links: ["skill-performance-testing-strategy-5501763d28"]
---

## Test Data Management

### Factories vs. Fixtures vs. Test Containers

| Approach | When to Use | Example |
|---|---|---|
| **Hardcoded values** | Simple, obvious test data | `user = User(name="Alice")` |
| **Factory functions** | Reusable, customizable test data | `user_factory(role="admin")` |
| **factory_boy** | Complex objects with relationships | `UserFactory(orders__count=3)` |
| **Fixtures (pytest)** | Shared infrastructure (DB session, HTTP client) | `@pytest.fixture(scope="session")` |
| **testcontainers** | Real service dependencies | PostgreSQL, Redis, Kafka, Azurite |

### Factory Pattern

```python
# factories.py
import factory
from faker import Faker
from myapp.models import User, Order

fake = Faker()

class UserFactory(factory.Factory):
    class Meta:
        model = User
    
    id = factory.LazyFunction(lambda: str(uuid4()))
    email = factory.LazyFunction(fake.email)
    name = factory.LazyFunction(fake.name)
    role = "user"
    
    class Params:
        admin = factory.Trait(role="admin")

# Usage
user = UserFactory()                    # default user
admin = UserFactory(admin=True)         # admin user
custom = UserFactory(email="user@example.com")  # specific email
```

### Test Data Isolation Rule
Never share mutable test data between tests. Each test creates its own data. Tests that share data are tests that depend on execution order — the definition of a fragile test suite.

---
