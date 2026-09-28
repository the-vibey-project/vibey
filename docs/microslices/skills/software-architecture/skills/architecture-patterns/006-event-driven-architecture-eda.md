---
id: skill-event-driven-architecture-eda-6a62bd0f75
purpose: event driven architecture eda
source: src/vibey_tools/skills/plugins/software-architecture/skills/architecture-patterns/SKILL.md
requires: ["skill-serverless-architecture-6e3a8ced63"]
links: ["skill-rest-101447aef9"]
---

## Event-Driven Architecture (EDA)

### Azure Messaging: Three First-Class Services

| Service | Job | Key Features |
|---|---|---|
| **Service Bus** | Enterprise queues/topics | Ordering (sessions), transactions, DLQ, scheduled messages, duplicate detection |
| **Event Grid** | Reactive pub/sub | MQTT v3.1.1/v5.0 broker (Namespaces), HTTP pull delivery, 24hr retry with exponential backoff |
| **Event Hubs** | High-throughput streaming | Kafka-compatible endpoint, consumer groups, Capture to ADLS/Blob |

Most real EDA architectures use all three: Event Hubs for ingestion, Service Bus for reliable work queues, Event Grid for reactive system events.

**Event Grid Namespaces note:** Standard tier and classic topics (Basic) are different resource models — Namespaces currently support Event Hubs as the only push destination for namespace topics.

**MQTT scale:** A single Event Grid namespace (40 throughput units) demonstrated 200,000 publishers + 200,000 subscribers at ~40,000 messages/second.

**Anti-pattern:** Using events for request/response where the caller needs an immediate consistent answer.

### Outbox Pattern
Solves the dual-write problem: write the business change and the outbox event in one local transaction, then relay to the broker. Required whenever you publish events from a write DB.

---

# PART 2: COMMUNICATION PATTERNS
