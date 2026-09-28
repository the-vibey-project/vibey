---
id: skill-19-quick-reference-868ab365c5
purpose: 19 quick reference
source: src/vibey_tools/skills/plugins/algorithms-deep-dive/skills/algo-reference/SKILL.md
requires: ["skill-18-the-canon-46b017ee1d"]
links: ["skill-20-sources-and-method-58e15c6df3"]
---

## §19. Quick Reference

### 19.1 The selection table

| Need | Use |
|---|---|
| Sequence, index access | **Dynamic array.** Default (§3 → `algo-data-structures`) |
| Queue / both ends | Deque or ring buffer (§3 → `algo-data-structures`) |
| Point lookup by key | **Hash map.** Default (§4 → `algo-data-structures`) |
| Ordered keys, ranges, successor | B-tree / balanced BST (§5 → `algo-data-structures`) |
| Keys on disk, read-heavy | **B+ tree** (§5.2 → `algo-data-structures`) |
| Keys on disk, write-heavy | **LSM tree** (+ Bloom filters) (§5.2 → `algo-data-structures`) |
| String keys with shared prefixes | Trie / ART (§5.3 → `algo-data-structures`) |
| Repeated min/max | Binary heap (§6 → `algo-data-structures`) |
| Top k of n | **Bounded heap, O(n log k)** (§6 → `algo-data-structures`) |
| k-th element | **Quickselect, O(n) avg** (§7.2 → `algo-core-algorithms`) |
| Connectivity / grouping | **Union-Find** (§5.3 → `algo-data-structures`) |
| Shortest path, unweighted | BFS (§9 → `algo-core-algorithms`) |
| Shortest path, non-negative | Dijkstra (§9 → `algo-core-algorithms`) |
| **Negative edge weights** | **Bellman-Ford** — Dijkstra is silently wrong (§9 → `algo-core-algorithms`) |
| Dependency order / cycle detection | Topological sort (§9 → `algo-core-algorithms`) |
| Many patterns, one pass | Aho-Corasick (§10 → `algo-core-algorithms`) |
| "Have I seen this?" at scale | Bloom / cuckoo filter (§12 → `algo-probabilistic-concurrency-and-measurement`) |
| "How many distinct?" at scale | **HyperLogLog** (§12 → `algo-probabilistic-concurrency-and-measurement`) |
| Percentiles over a stream | t-digest / DDSketch (§12 → `algo-probabilistic-concurrency-and-measurement`) |
| Near-duplicate detection | MinHash / SimHash (§10 → `algo-core-algorithms`, §12 → `algo-probabilistic-concurrency-and-measurement`) |
| Large set intersection | **Roaring bitmaps** (§8 → `algo-core-algorithms`) |
| High-dimensional similarity | **HNSW / DiskANN + quantization** (§13.4 → `algo-probabilistic-concurrency-and-measurement`) |
| Geospatial | R-tree, S2/H3 (§8 → `algo-core-algorithms`) |
| Shared mutable state | **Try not sharing first**, then a mutex (§14 → `algo-probabilistic-concurrency-and-measurement`) |

### 19.2 Numbers to keep in your head
- **Cache line: 64 bytes.** L1 ~4 cycles, DRAM ~200–300. **The cliff is DRAM.**
- **Branch mispredict: ~15–20 cycles.**
- **Heapify is O(n)**, not O(n log n).
- **Comparison sorting is Ω(n log n)**; radix isn't comparison-based.
- **Hash maps resize around 0.7–0.9 load** — and that's an O(n) latency spike.
- **k-d trees degrade above ~20 dimensions.**
- **HLL: ~2% error, kilobytes, billions of items, mergeable.**
- **Amortized O(1) is your p99 problem, not your average-case win.**

### 19.3 Before optimizing
- [ ] Have I profiled, or am I guessing? (§13 → `algo-probabilistic-concurrency-and-measurement`)
- [ ] What fraction of runtime is this? (Amdahl)
- [ ] Is the problem the algorithm, or the memory layout? (§2 → `algo-foundations-and-machine-model`)
- [ ] Am I benchmarking across input sizes? (§2.1 → `algo-foundations-and-machine-model`)
- [ ] Realistic data and distribution?
- [ ] Reporting the distribution, not the mean?
- [ ] Would a different structure make the algorithm trivial? (§1 → `algo-foundations-and-machine-model`)
- [ ] Would approximation be acceptable? (§12 → `algo-probabilistic-concurrency-and-measurement`)
- [ ] Is the standard library's default actually wrong for my data, or do I just assume so?

---
