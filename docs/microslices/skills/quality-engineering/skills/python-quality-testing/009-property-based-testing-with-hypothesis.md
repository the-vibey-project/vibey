---
id: skill-property-based-testing-with-hypothesis-34767fbc51
purpose: property based testing with hypothesis
source: src/vibey_tools/skills/plugins/quality-engineering/skills/python-quality-testing/SKILL.md
requires: ["skill-contract-testing-with-pact-886c18bf74"]
links: ["skill-mutation-testing-1ec2aedb26"]
---

## Property-Based Testing with Hypothesis

Hypothesis (David MacIver, JOSS 2019) finds edge cases that example-based tests miss by generating thousands of random inputs and shrinking failures to minimal examples.

### Basic Usage

```python
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

@given(
    price=st.decimals(min_value=0, max_value=10000, places=2),
    quantity=st.integers(min_value=1, max_value=1000)
)
def test_order_total_always_positive(price, quantity):
    """No matter what valid price and quantity, total is always positive."""
    order = Order(price=price, quantity=quantity)
    assert order.total() > 0

@given(st.text(min_size=1, max_size=255))
def test_product_name_round_trips_through_db(name, db_session):
    """Any valid name saved to DB should come back identical."""
    product = Product(name=name)
    db_session.add(product)
    db_session.flush()
    retrieved = db_session.get(Product, product.id)
    assert retrieved.name == name
```

### Stateful Testing (RuleBasedStateMachine)

```python
from hypothesis.stateful import RuleBasedStateMachine, rule, initialize, invariant

class ShoppingCartMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.cart = ShoppingCart()
        self.model_items = {}  # simple model to verify against
    
    @initialize(product_id=st.uuids(), price=st.decimals(min_value=0.01, max_value=999.99, places=2))
    def setup_product(self, product_id, price):
        self.product_catalog = {str(product_id): price}
    
    @rule(product_id=st.uuids(), quantity=st.integers(min_value=1, max_value=10))
    def add_item(self, product_id, quantity):
        pid = str(product_id)
        if pid in self.product_catalog:
            self.cart.add_item(pid, quantity)
            self.model_items[pid] = self.model_items.get(pid, 0) + quantity
    
    @invariant()
    def cart_total_matches_model(self):
        expected = sum(
            self.product_catalog[pid] * qty
            for pid, qty in self.model_items.items()
            if pid in self.product_catalog
        )
        assert self.cart.total() == expected

TestShoppingCart = ShoppingCartMachine.TestCase
```

### When to Use Hypothesis
- **Pure functions** — math operations, data transformations, serialization/deserialization
- **Parsers and validators** — should never crash on valid input; should reject invalid input consistently
- **Round-trip properties** — encode/decode, serialize/deserialize, save/retrieve
- **Ordering and sorting** — verify invariants hold across random inputs
- **State machines** — model-based testing of complex stateful systems

**Hypothesis's shrinking** is what makes it valuable: when it finds a failing input, it automatically reduces it to the minimal case that still fails. The failure `price=0.00001` shrinks to `price=0` if that's the actual bug.

---
