---
id: skill-event-streaming-kafka-pattern-e7ec7e8967
purpose: event streaming kafka pattern
source: src/vibey_tools/skills/plugins/software-architecture/skills/architecture-patterns/SKILL.md
requires: ["skill-message-queues-d9471f62fa"]
links: ["skill-relational-rdbms-b5902985cf"]
---

## Event Streaming (Kafka Pattern)
- Immutable append-only log; consumer groups track own offset; partitions = parallelism; compaction maintains latest-state
- **Azure Event Hubs**: Kafka-compatible endpoint (no code change), consumer groups, **Capture** to ADLS/Blob, Standard/Premium/Dedicated tiers
- **Confluent Cloud on Azure vs Event Hubs**: Confluent for full Kafka ecosystem (Connect, ksqlDB, Schema Registry, exactly-once Streams); Event Hubs for managed, lower-ops Azure-native ingestion

---

# PART 3: DATA ARCHITECTURE PATTERNS
