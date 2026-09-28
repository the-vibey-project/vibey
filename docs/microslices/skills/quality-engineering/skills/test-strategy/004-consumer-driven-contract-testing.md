---
id: skill-consumer-driven-contract-testing-bf5fe2b3f9
purpose: consumer driven contract testing
source: src/vibey_tools/skills/plugins/quality-engineering/skills/test-strategy/SKILL.md
requires: ["skill-tdd-vs-bdd-vs-atdd-when-to-use-each-c76976e23a"]
links: ["skill-property-based-testing-with-hypothesis-00be087fe4"]
---

## Consumer-Driven Contract Testing

### When to Use Contract Testing
Use contract testing when you have **microservices with separate deployment cycles**. If services are always deployed together, you don't need contract tests. If a service can be deployed independently, you need to know its contracts are satisfied before deployment.

**The problem contract testing solves:** Service A consumes Service B's API. Service B adds a new required field. Service A deploys without knowing. Production breaks.

### The Pact Flow

```
CONSUMER SIDE                          PROVIDER SIDE
─────────────                          ─────────────
1. Write interaction test              4. Provider downloads pacts
   (expected request + response)           from Pact Broker
        ↓                                     ↓
2. Pact generates contract             5. Provider verifier runs
   (.json pact file)                       against real provider code
        ↓                                     ↓
3. Publish to Pact Broker              6. Publish verification results
        ↓                                     ↓
                    7. can-i-deploy checks compatibility
                       before any deployment to production
```

### Key Principles

**Consumer-driven contracts mean consumers set the rules.** The consumer defines what it needs from the provider. The provider must satisfy those needs. This inverts the traditional approach where providers define APIs and consumers adapt.

**Pact Broker is required for multi-team use.** The broker stores contracts, verification results, and enables the `can-i-deploy` gate.

**can-i-deploy is the deployment gate:**
```bash
# This command asks: "Can OrderService v1.2.3 be deployed to production?"
# It checks all consumer contracts are verified for this version
pact-broker can-i-deploy \
  --pacticipant OrderService \
  --version 1.2.3 \
  --to-environment production
# Returns: 0 (can deploy) or 1 (cannot deploy, contract violations exist)
```

### What Contract Tests Do NOT Cover
- Performance characteristics of the provider
- Business logic inside the provider
- Error scenarios beyond what the consumer test specifies
- Non-functional requirements

Contract tests verify **compatibility**, not **correctness**. You still need integration and E2E tests.

---
