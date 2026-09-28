---
id: skill-monolith-first-doctrine-64ccf8665a
purpose: monolith first doctrine
source: src/vibey_tools/skills/plugins/software-architecture/skills/software-design/SKILL.md
requires: ["skill-architectural-design-patterns-and-styles-02c80a309c"]
links: ["skill-domain-driven-design-ddd-ea51814190"]
---

## Monolith-First Doctrine

### The Mainstream Consensus (2024–2026)
Start with a well-factored modular monolith. Extract services only when concrete pain justifies the distributed-systems tax.

**Martin Fowler's MonolithFirst:**
> "You should build a new application as a monolith initially, even if you think it's likely that it will benefit from a microservices architecture later on."

Citing Simon Brown: "If you can't build a well-structured monolith, what makes you think you can build a well-structured set of microservices?"

**DHH's Majestic Monolith:**
> "The vast majority of web applications should start life as a Majestic Monolith."

**Shopify's canonical case:** Core monolith of over 2.8 million lines of Ruby and 500,000 commits, reorganized into 37 components using the open-sourced **Packwerk** tool to enforce dependency and privacy boundaries. Shopify's Kirsten Westeinde: "I would actually recommend that new products and new companies start with a monolith."

**Amazon Prime Video case (Kolny, 2023):** Moving one internal audio/video monitoring pipeline from microservices to a monolith "reduced our infrastructure cost by over 90% [and] increased our scaling capabilities." Critically, Kolny explicitly cautioned this was not a company-wide recommendation. Amazon CTO Werner Vogels: "Building evolvable software systems is a strategy, not a religion."

**Thoughtworks Radar:** "It's often advisable to start with a well-factored monolith and only break out separately deployable units when the application reaches a scale where the benefits of microservices outweigh the additional complexity inherent in distributed systems."

### The Distributed Monolith — The Worst Failure Mode
Sam Newman: "Microservices should not be the default choice." The worst outcome is **the distributed monolith** — many services that must be deployed together.

Tell-tale sign: someone has a full-time job as "release coordination manager." Caused by splitting along technical layers rather than business/domain boundaries.

> **Benchmark:** If a "release coordination manager" role appears → you have a distributed monolith; stop splitting and re-modularize.

### Threshold to Escalate to Microservices
Extract a service only when you feel **concrete pain**:
- Independent deployability is blocked by the monolith
- Divergent scaling needs that cannot be addressed in-process
- Team-autonomy bottlenecks requiring separate deployment pipelines

**AND** you have the operational maturity (observability, CI/CD) to pay the distributed-systems tax.

---
