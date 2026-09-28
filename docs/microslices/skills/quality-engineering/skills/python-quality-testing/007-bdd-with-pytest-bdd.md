---
id: skill-bdd-with-pytest-bdd-df49ce9f51
purpose: bdd with pytest bdd
source: src/vibey_tools/skills/plugins/quality-engineering/skills/python-quality-testing/SKILL.md
requires: ["skill-tdd-red-green-refactor-72bf781e1e"]
links: ["skill-contract-testing-with-pact-886c18bf74"]
---

## BDD with pytest-bdd

```gherkin
# features/checkout.feature
Feature: Shopping cart checkout

  Scenario: Successful checkout with valid payment
    Given a shopping cart with 2 items totaling $45.00
    And the customer has a valid payment method on file
    When the customer completes checkout
    Then the order is created with status "CONFIRMED"
    And the customer receives a confirmation email
```

```python
# tests/test_checkout.py
from pytest_bdd import given, when, then, scenario

@scenario('features/checkout.feature', 'Successful checkout with valid payment')
def test_checkout_success():
    pass

@given("a shopping cart with 2 items totaling $45.00")
def cart_with_items(cart_factory):
    return cart_factory(items=2, total=Decimal("45.00"))

@when("the customer completes checkout")
def complete_checkout(cart, payment_service):
    return checkout_service.process(cart, payment_service)

@then('the order is created with status "CONFIRMED"')
def verify_order_status(checkout_result):
    assert checkout_result.order.status == "CONFIRMED"
```

**Three Amigos for ATDD:** Developer + Tester + Business Analyst define Gherkin scenarios before any code is written. This is **Acceptance Test-Driven Development** — the spec is the test.

---
