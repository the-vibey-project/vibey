---
id: skill-enterprise-integration-patterns-eip-hohpe-woolf-eb1b4e5096
purpose: enterprise integration patterns eip hohpe woolf
source: src/vibey_tools/skills/plugins/software-architecture/skills/architecture-patterns/SKILL.md
requires: ["skill-prompt-flow-retirement-b7e0a8d8f1"]
links: ["skill-workflow-orchestration-8fb0d8af62"]
---

## Enterprise Integration Patterns (EIP) — Hohpe & Woolf
Key patterns implemented in Azure:
- **Message Channel, Router, Translator, Filter**: Service Bus native
- **Splitter, Aggregator, Scatter-Gather**: Durable Functions for stateful aggregation
- **Dead Letter Channel**: Service Bus DLQ
- **Idempotent Receiver**: Duplicate detection + idempotency keys
- **Competing Consumers**: Service Bus + KEDA auto-scaling
