---
id: skill-performance-testing-strategy-5501763d28
purpose: performance testing strategy
source: src/vibey_tools/skills/plugins/quality-engineering/skills/test-strategy/SKILL.md
requires: ["skill-test-data-management-fa76c76ab6"]
links: ["skill-security-testing-integration-a3cc83ba37"]
---

## Performance Testing Strategy

Performance testing is not a single test type — it is a progression:

| Test Type | Purpose | When to Run |
|---|---|---|
| **Baseline** | Establish normal performance under expected load | Before any load testing |
| **Load** | Verify system performs under expected traffic | Every release for critical services |
| **Stress** | Find the breaking point | Quarterly for capacity planning |
| **Soak/Endurance** | Find memory leaks, resource exhaustion | Before major releases |
| **Spike** | Verify recovery from sudden traffic increases | Before marketing campaigns |

**Locust for Python load testing:**
```python
from locust import HttpUser, task, between

class APIUser(HttpUser):
    wait_time = between(0.5, 2.0)
    
    @task(3)  # runs 3x more often than weight 1 tasks
    def get_products(self):
        self.client.get("/api/products?page=1&size=20")
    
    @task(1)
    def create_order(self):
        self.client.post("/api/orders", json={
            "productId": "PROD-123",
            "quantity": 1
        })
```

**Defining pass/fail criteria** (required for CI integration):
```python
# locust pass/fail criteria
--headless
--users 100
--spawn-rate 10
--run-time 60s
--html report.html
# Exit codes: 0=pass, 1=fail (if Locust thresholds exceeded)
# Configure in locust.conf: stop-on-fail, exit-code-on-error
```

---
