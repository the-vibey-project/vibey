---
id: skill-message-queues-d9471f62fa
purpose: message queues
source: src/vibey_tools/skills/plugins/software-architecture/skills/architecture-patterns/SKILL.md
requires: ["skill-websockets-real-time-f0b2ac45bc"]
links: ["skill-event-streaming-kafka-pattern-e7ec7e8967"]
---

## Message Queues
- **Service Bus Queues**: sessions for FIFO/ordering, duplicate detection, DLQ, scheduled messages, transactions
  - **Premium**: VNet isolation, messages **up to 100 MB (AMQP only; must raise default 1 MB)**
  - **Standard/Basic**: 256 KB message limit
- **Storage Queues**: cheap, simple, high-volume alternative
- Poison messages auto-move to DLQ after max delivery count
