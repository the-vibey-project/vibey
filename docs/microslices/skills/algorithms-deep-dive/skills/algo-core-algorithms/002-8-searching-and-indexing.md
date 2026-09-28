---
id: skill-8-searching-and-indexing-aad33f628c
purpose: 8 searching and indexing
source: src/vibey_tools/skills/plugins/algorithms-deep-dive/skills/algo-core-algorithms/SKILL.md
requires: ["skill-7-sorting-596359c307"]
links: ["skill-9-graphs-501de76684"]
---

## §8. Searching and Indexing

**Binary search** — O(log n), and **⚠️ notoriously easy to get wrong** (the overflow in
`(lo+hi)/2` shipped in the JDK for years). **Use the library.** The variants that matter
are `lower_bound`/`upper_bound` — "first element ≥ x" is more often what you want than
"is x present."

**⚠️ Interpolation search** is O(log log n) on uniform data and O(n) on skewed data.
**Branchless / Eytzinger-layout binary search** rearranges the array in BFS order for
better cache behaviour — a real win for repeated searches on a static array.

**Inverted indexes** — the core of full-text search: term → posting list, with
skip pointers, compression (delta + varint/PFOR), and scoring (BM25). **If you're building
search, you're building this or using Lucene.**

**Bitmap indexes** — **Roaring bitmaps** are the practical standard: hybrid
array/bitmap/run containers, and **the right answer for large set intersection**,
which is what filtered search reduces to.

**Spatial indexes** — R-trees (rectangles, the standard in spatial DBs), k-d trees
(⚠️ **degrade badly above ~20 dimensions** — the curse of dimensionality), quadtrees /
octrees, **geohash and S2/H3** for lat-long. Which is why high-dimensional similarity
needs an entirely different approach (§13.4 → `algo-probabilistic-concurrency-and-measurement`).

---
