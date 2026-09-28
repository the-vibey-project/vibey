---
id: skill-batch-vs-streaming-decision-575c4e0f62
purpose: batch vs streaming decision
source: src/vibey_tools/skills/plugins/ai-and-data/skills/data-engineering/SKILL.md
requires: ["skill-data-quality-at-scale-pydantic-vs-pandera-b3273d4bd2"]
links: ["skill-sql-cte-best-practices-f41e989296"]
---

## Batch vs Streaming Decision

| Need | Recommendation |
|---|---|
| Sub-second latency, business acts on it (fraud, dynamic pricing) | True streaming (Flink or Kafka + consumer) |
| Seconds of latency acceptable | Micro-batch (Spark Structured Streaming) |
| Minutes/hours acceptable | Batch ELT |

**Flink**: true event-at-a-time, p99 latencies <100ms; more resource-efficient for low-latency.
**Spark Streaming**: ~2–5s; wins when you share resources across batch and streaming or already run Databricks/Delta.

**Cost lever**: BigQuery streaming costs $0.01/200MB; micro-batch loading is free — a major difference at scale.

---
