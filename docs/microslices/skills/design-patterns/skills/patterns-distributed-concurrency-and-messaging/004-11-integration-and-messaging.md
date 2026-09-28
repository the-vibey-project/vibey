---
id: skill-11-integration-and-messaging-a44a5701fe
purpose: 11 integration and messaging
source: src/vibey_tools/skills/plugins/design-patterns/skills/patterns-distributed-concurrency-and-messaging/SKILL.md
requires: ["skill-10-concurrency-patterns-7ddc3dad7f"]
links: []
---

## §11. Integration and Messaging

**[DURABLE] Hohpe & Woolf's *Enterprise Integration Patterns* (2003) named these, and the
vocabulary is still the industry standard 20+ years on** — a genuine counterexample to
"patterns don't age."

**Message channel**, **publish-subscribe**, **point-to-point**, **message router**,
**content-based router**, **message translator**, **message filter**, **splitter and
aggregator**, **scatter-gather**, **process manager**, **claim check** (⚠️ **put the large
payload in storage and pass a reference** — the fix for oversized messages), **competing
consumers**, **dead letter channel**, **guaranteed delivery**.

**Delivery semantics, precisely:** **at-most-once** (may lose), **at-least-once** (may
duplicate — **the practical default**), **exactly-once** (⚠️ **not achievable end-to-end
in the general case** — what systems offer is at-least-once delivery plus idempotent
processing, which is the achievable and correct target).

**Event flavours matter and are frequently confused**: **event notification** (something
happened, go look), **event-carried state transfer** (the event includes the data),
**event sourcing** (§8). **Choosing the wrong one is a common source of coupling** —
event-carried state transfer looks convenient and quietly couples consumers to your
internal schema.
