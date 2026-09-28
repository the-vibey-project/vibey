---
id: skill-black-box-test-design-techniques-1d068a0615
purpose: black box test design techniques
source: src/vibey_tools/skills/plugins/quality-engineering/skills/python-quality-testing/SKILL.md
requires: ["skill-iso-iec-25010-2023-quality-characteristics-1d07042353"]
links: ["skill-pytest-the-complete-reference-dd27bcd55e"]
---

## Black-Box Test Design Techniques

Four foundational techniques defined in ISTQB CTFL v4.0 (2023) and ISO/IEC/IEEE 29119-4:2021. These are tool-agnostic and should inform pytest parametrize design.

### 1. Equivalence Partitioning (EP)
Divide input space into classes treated identically by the software. Write one test per partition.

```python
# Discount tiers: 0-99 items (no discount), 100-499 (10%), 500+ (20%)
@pytest.mark.parametrize("quantity,expected_discount", [
    (0, 0.0),       # below minimum — invalid partition
    (50, 0.0),      # no-discount partition
    (150, 0.10),    # 10% partition
    (600, 0.20),    # 20% partition
])
def test_discount_by_quantity(quantity, expected_discount):
    assert calculate_discount(quantity) == expected_discount
```

### 2. Boundary Value Analysis (BVA)
Test at and around partition boundaries. ISTQB distinguishes:
- **2-value BVA**: test at boundary and just inside the next partition
- **3-value BVA**: test just below, at, and just above each boundary

```python
@pytest.mark.parametrize("quantity,expected_discount", [
    (99, 0.0),    # just below first boundary
    (100, 0.10),  # at first boundary
    (101, 0.10),  # just above first boundary
    (499, 0.10),  # just below second boundary
    (500, 0.20),  # at second boundary
    (501, 0.20),  # just above second boundary
])
def test_discount_boundaries(quantity, expected_discount):
    assert calculate_discount(quantity) == expected_discount
```

### 3. Decision Table Testing
For complex business logic with multiple conditions, enumerate all condition combinations. Each column is a test case.

| Condition | T1 | T2 | T3 | T4 |
|---|---|---|---|---|
| Has loyalty card | Y | Y | N | N |
| Purchase > $100 | Y | N | Y | N |
| **Expected discount** | **15%** | **5%** | **10%** | **0%** |

Decision tables guarantee systematic coverage of logical branches.

### 4. State Transition Testing
Model the system as states, transitions, and events. Verify all transitions.

```python
# Order states: PENDING → CONFIRMED → SHIPPED → DELIVERED
# Each transition should have a test
@pytest.mark.parametrize("from_state,event,to_state", [
    ("PENDING", "confirm", "CONFIRMED"),
    ("CONFIRMED", "ship", "SHIPPED"),
    ("SHIPPED", "deliver", "DELIVERED"),
    ("PENDING", "cancel", "CANCELLED"),
    # Invalid transitions should raise
])
def test_order_state_transitions(from_state, event, to_state, order_factory):
    order = order_factory(state=from_state)
    order.apply_event(event)
    assert order.state == to_state
```

---
