---
id: skill-12-probabilistic-and-streaming-structures-71c65da736
purpose: 12 probabilistic and streaming structures
source: src/vibey_tools/skills/plugins/algorithms-deep-dive/skills/algo-probabilistic-concurrency-and-measurement/SKILL.md
requires: []
links: ["skill-13-measurement-b3c762c39f"]
---

## §12. Probabilistic and Streaming Structures

**[DURABLE] These trade a bounded, quantified error for enormous savings in space or time,
and they are dramatically under-used relative to how often they fit.**

| Structure | Answers | Trades |
|---|---|---|
| **Bloom filter** | "Definitely not present" / "probably present" | ⚠️ **False positives, never false negatives.** No deletion |
| **Counting / Cuckoo filter** | Same, with deletion | More space; cuckoo also gives better locality |
| **HyperLogLog** | Approximate cardinality | ~2% error in **kilobytes** for billions of items. Mergeable |
| **Count-Min Sketch** | Approximate frequency | Overestimates only; heavy-hitters |
| **t-digest / DDSketch** | Approximate quantiles | ⚠️ **What your metrics system uses for p99** |
| **MinHash / SimHash** | Set/document similarity | Near-duplicate detection at scale |
| **Reservoir sampling** | Uniform sample from a stream of unknown length | One pass, O(k) space |

**[DURABLE] The canonical use**: **Bloom filters in front of LSM-tree reads** (§5.2 → `algo-data-structures`), so a
lookup skips levels that definitely don't contain the key. That single application is why
write-optimized stores can also read acceptably.

**⚠️ Know the error model before deploying.** "2% error" on a cardinality estimate is fine
for a dashboard and unacceptable for billing. **The question is always: what does being
wrong cost here?**

---
