---
id: skill-contract-testing-with-pact-886c18bf74
purpose: contract testing with pact
source: src/vibey_tools/skills/plugins/quality-engineering/skills/python-quality-testing/SKILL.md
requires: ["skill-bdd-with-pytest-bdd-df49ce9f51"]
links: ["skill-property-based-testing-with-hypothesis-34767fbc51"]
---

## Contract Testing with Pact

Consumer-driven contract testing prevents microservice integration breakage. The consumer defines expected interactions; the provider proves it can satisfy them.

### The Pact Flow

```
1. Consumer test creates interaction expectations
       ↓
2. Pact generates a .json contract file
       ↓
3. Contract published to Pact Broker
       ↓
4. Provider verification tests run against the Broker
       ↓
5. can-i-deploy gates deployment on contract compatibility
```

### Consumer Side (pact-python, Rust-backed via Pact FFI, v4 spec)

```python
# tests/consumer/test_order_client.py
import pytest
from pact import Consumer, Provider

@pytest.fixture(scope="session")
def pact():
    pact = Consumer('OrderService').has_pact_with(
        Provider('InventoryService'),
        host_name='localhost',
        port=1234,
        pact_dir='./pacts'
    )
    pact.start_service()
    yield pact
    pact.stop_service()

def test_get_product_stock(pact):
    expected = {"productId": "PROD-123", "quantity": 42, "available": True}
    
    (pact
     .given("product PROD-123 has 42 units in stock")
     .upon_receiving("a request for product stock")
     .with_request("GET", "/inventory/PROD-123")
     .will_respond_with(200, body=expected))
    
    with pact:
        result = inventory_client.get_stock("PROD-123")
        assert result.available is True
        assert result.quantity == 42
```

### Provider Verification

```python
# tests/provider/test_inventory_provider.py
import pytest
from pact import Verifier

def test_provider_pacts():
    verifier = Verifier(
        provider='InventoryService',
        provider_base_url='http://localhost:8080'
    )
    output, _ = verifier.verify_with_broker(
        broker_url='https://pact.myorg.com',
        publish_verification_results=True,
        provider_version='1.2.3'
    )
    assert output == 0  # 0 = all pacts verified
```

**Use `can-i-deploy` in CI/CD** to gate deployments on contract compatibility:
```bash
pact-broker can-i-deploy \
  --pacticipant OrderService \
  --version $GIT_SHA \
  --to-environment production
```

---
