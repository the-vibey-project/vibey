---
id: skill-4-the-social-graph-6ddbd4cf5b
purpose: 4 the social graph
source: src/vibey_tools/skills/plugins/social-media-engineering/skills/social-feed-graph-ranking-and-notifications/SKILL.md
requires: ["skill-3-feed-and-timeline-architecture-a2b42050b1"]
links: ["skill-5-ranking-and-recommendation-b0c477387c"]
---

## §4. The Social Graph

**[DURABLE]** **Directed** (follow: Twitter, Instagram) vs **undirected** (friend:
Facebook) — ⚠️ **and the choice cascades into privacy, feeds, and moderation in ways that
are painful to reverse.**

**Storage**: adjacency lists in a KV store, a relational table with careful indexing,
a graph database (Neo4j, or Meta's TAO-style approach), or **an adjacency-list service
with heavy caching** — ⚠️ **which is what most large systems actually build, because a
general graph database is usually the wrong tool for a workload that is 99% "get followers
of X."**

**⚠️ The operations that hurt**: **follower counts on celebrity accounts** (⚠️ **counting
is expensive — cache approximately, and accept eventual consistency**), **"do these two
users follow each other"** at scale, **mutual-follow and friends-of-friends** queries, and
**the fact that graph traversal depth explodes combinatorially** — two hops from a
well-connected node is most of the network.

**Privacy is a graph problem**: blocks must be bidirectional in effect; **⚠️ private
accounts mean visibility checks on every read path, and getting one path wrong is a data
leak** rather than a bug.

---
