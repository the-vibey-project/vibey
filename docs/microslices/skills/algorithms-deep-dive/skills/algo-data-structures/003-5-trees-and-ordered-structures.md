---
id: skill-5-trees-and-ordered-structures-804ed6ec93
purpose: 5 trees and ordered structures
source: src/vibey_tools/skills/plugins/algorithms-deep-dive/skills/algo-data-structures/SKILL.md
requires: ["skill-4-hash-tables-300dc0e57b"]
links: ["skill-6-heaps-and-priority-queues-b0c0aaaba3"]
---

## §5. Trees and Ordered Structures

### 5.1 In-memory trees

**[DURABLE] Use a tree when you need order** — range queries, successor/predecessor,
min/max, sorted iteration. **If you only need point lookup, use a hash map** (§4); a tree
is strictly worse for that.

**Balanced BSTs**: red-black (the usual standard-library choice — `std::map`,
`TreeMap`), AVL (more strictly balanced, faster lookup, slower update), **B-trees**
(§5.2 — increasingly used *in memory* too, because of §2 → `algo-foundations-and-machine-model`), **splay** (self-adjusting,
excellent for skewed access, ⚠️ **mutates on read**, which is a concurrency landmine),
**treaps** and **skip lists** (randomized, much simpler to implement, and skip lists are
notably easier to make concurrent).

**⚠️ The modern caveat**: **binary trees have poor cache behaviour** — one node per cache
line, one miss per level. **This is why B-trees with fanout tuned to the cache line
(B+ trees, or "cache-conscious" layouts) increasingly beat binary trees in memory**, and
why Rust's `BTreeMap` is a B-tree rather than a red-black tree.

### 5.2 B-trees and the storage divide

**[DURABLE] B-trees are the correct structure for block-addressed storage**, and
essentially every relational database index is one. High fanout (hundreds of keys per
node), so a billion rows is 3–4 levels deep and the upper levels stay cached. **B+ trees**
put all data in leaves and link them — which is what makes range scans fast.

**LSM trees** are the other half of the storage world (LevelDB, RocksDB, Cassandra,
ScyllaDB, and most modern write-heavy stores). **Buffer writes in memory, flush sorted
runs to disk, compact in the background.**

**[DURABLE] The trade-off is the clearest example of RUM in practice** (§16.1 → `algo-reference`):

| | **B-tree** | **LSM tree** |
|---|---|---|
| Writes | In-place, random I/O | **Sequential, much faster** |
| Reads | One path, predictable | May check several levels; **needs Bloom filters** (§12 → `algo-probabilistic-concurrency-and-measurement`) |
| Space | Fragmentation | ⚠️ **Space amplification** until compaction |
| Latency | Predictable | ⚠️ **Compaction causes spikes** |
| Best for | Read-heavy, range-heavy | **Write-heavy ingest** |

**⚠️ Know the three amplification factors** — read, write, and space — because a storage
engine choice is choosing which one to pay. Tuning an LSM is largely compaction tuning, and
**compaction stalls are the characteristic production surprise.**

### 5.3 Specialized trees
**Tries / radix trees** — string keys with shared prefixes; prefix and autocomplete
queries. **Adaptive Radix Tree (ART)** is the cache-efficient modern version.
**Segment trees / Fenwick (BIT)** — range queries with updates; Fenwick is smaller and
faster for prefix sums. **Interval trees** — overlap queries. **Merkle trees** —
verification and diffing, everywhere in distributed systems and version control.
**Union-Find (disjoint set)** — connectivity, Kruskal's, and **near-constant time with
path compression + union by rank**. ⚠️ **Under-known relative to how often it's exactly
the right tool.**

---
