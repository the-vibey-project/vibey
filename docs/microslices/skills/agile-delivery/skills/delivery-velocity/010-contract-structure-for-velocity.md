---
id: skill-contract-structure-for-velocity-06707ba4b7
purpose: contract structure for velocity
source: src/vibey_tools/skills/plugins/agile-delivery/skills/delivery-velocity/SKILL.md
requires: ["skill-what-to-eliminate-41a9561f7f"]
links: ["skill-dora-elite-benchmarks-b632e5b0cf"]
---

## Contract Structure for Velocity

### The Evidence

Jørgensen et al. (2017, *International Journal of Project Management*): **fixed-price contracts are connected with a higher risk of project failure** compared to T&M contracts. Mechanism: fixed-price requires extensive upfront specification before any code is written, freezes scope based on flawed initial understanding, and creates adversarial dynamics around change requests.

McKinsey: IT projects are delayed by **59% on average**, largely due to rigid scope commitments.

### Optimal Contract Model

**Time-and-materials with fixed-time iterations and a monthly budget cap:**
- Team bills for actual hours worked within 2-week cycles
- Scope negotiated at the start of each cycle based on deployed learnings
- Client pays for velocity, not for a specification document
- Monthly budget cap provides cost predictability without scope rigidity
- Formal scope review at each cycle boundary: client can reprioritize, add, or cut features

**Deliverable per cycle:** number of deployed increments (working software in production), not a scope specification.

This model aligns incentives: consultancy is paid for shipping; client gets steering flexibility.

---
