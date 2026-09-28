---
id: skill-3-feed-and-timeline-architecture-a2b42050b1
purpose: 3 feed and timeline architecture
source: src/vibey_tools/skills/plugins/social-media-engineering/skills/social-feed-graph-ranking-and-notifications/SKILL.md
requires: []
links: ["skill-4-the-social-graph-6ddbd4cf5b"]
---

## §3. Feed and Timeline Architecture

**[DURABLE] The canonical distributed-systems problem in this domain, and the trade-off is
stable.**

```
FAN-OUT ON WRITE (push)          FAN-OUT ON READ (pull)
Write to every follower's        Query followers' posts at read time
timeline at post time
✓ Reads are fast and cheap       ✓ Writes are cheap
✗ ⚠️ A 50M-follower account      ✗ Reads are expensive and hard to cache
  means 50M writes
✗ Storage amplification          ✗ Latency scales with following count
```

**[DURABLE] Every real system is hybrid**: **fan-out on write for normal accounts,
fan-out on read for high-follower accounts, merged at read time.** ⚠️ **The threshold is a
tuning parameter, and "celebrity accounts" are a distinct architectural case you must plan
for rather than discover.**

**The implementation vocabulary**: **timeline as a materialized list of post IDs**
(⚠️ **store IDs, hydrate content at read — content changes, deletions, and blocks all
become tractable**), **Redis or a purpose-built store** for the timeline itself,
**async fan-out through a queue**, **cursor-based pagination** (⚠️ **never offset — new
posts shift the window and you get duplicates and gaps**), and **backfill and repair jobs**
because fan-out will drop things.

**⚠️ The details that bite**: **deletion and edit propagation** through already-fanned-out
timelines; **block and mute enforcement** at read time (⚠️ **applying blocks at write time
means a later block doesn't retroactively clean the timeline**); **the "new follower
backfill" question** (do they see history?); **and the cold-start empty feed**, which is a
product problem disguised as an engineering one.

---
