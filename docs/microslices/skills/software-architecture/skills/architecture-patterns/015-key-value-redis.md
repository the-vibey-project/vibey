---
id: skill-key-value-redis-90e5ca50cb
purpose: key value redis
source: src/vibey_tools/skills/plugins/software-architecture/skills/architecture-patterns/SKILL.md
requires: ["skill-document-cosmos-db-for-nosql-4cac6b32b5"]
links: ["skill-vector-search-3bc6f56154"]
---

## Key-Value (Redis)
- **Azure Cache for Redis / Azure Managed Redis**: Basic/Standard/Premium/Enterprise/Enterprise Flash
- Clustering, geo-replication, modules (**RediSearch, RedisJSON, RedisTimeSeries**) on Enterprise tier
- RediSearch powers APIM semantic caching

**Caching patterns:**
| Pattern | How It Works | Use When |
|---|---|---|
| Cache-aside (lazy loading) | App checks cache, loads on miss, populates | Most common default |
| Write-through | Write cache + DB together | Need consistency, can accept write latency |
| Write-behind | Write cache, async flush | Need write speed, can tolerate durability risk |
| Read-through | Cache fetches transparently | Simplify app code |
| Refresh-ahead | Proactively refresh before expiry | Predictable access patterns |

**Thundering herd / cache stampede:** Mitigate with probabilistic early expiration or a mutex on cache rebuild.
