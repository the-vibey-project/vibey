---
id: skill-3-arrays-and-sequences-fb56bba55a
purpose: 3 arrays and sequences
source: src/vibey_tools/skills/plugins/algorithms-deep-dive/skills/algo-data-structures/SKILL.md
requires: []
links: ["skill-4-hash-tables-300dc0e57b"]
---

## §3. Arrays and Sequences

**[DURABLE] The dynamic array (vector, `ArrayList`, `Vec`, slice) is the correct default
for sequences, and it is under-used relative to how often it's the right answer.**
Amortized O(1) append via geometric growth, O(1) indexing, and — decisively — **perfect
cache behaviour**.

| Structure | Real trade-off |
|---|---|
| **Dynamic array** | ⚠️ O(n) insert/delete in the middle — **but with a tiny constant**, so it wins over a list up to surprisingly large n |
| **Linked list** | O(1) splice **if you already hold the node**. ⚠️ Otherwise almost always the wrong choice — one cache miss per node, high per-element overhead. **Its main legitimate uses are intrusive lists and LRU chains where you hold node pointers** |
| **Deque** | O(1) both ends; usually a ring buffer or a chunked array. **The right answer for queues** |
| **Ring buffer** | Fixed capacity, contiguous, no allocation. **Excellent for streaming, audio, and bounded queues** |
| **Rope / gap buffer** | Text editing. Gap buffer for a single cursor, rope for concurrent/large edits |
| **Small-vector optimization** | Inline storage for the first N elements, heap after. **Large real win** for many-small-collections workloads |

**⚠️ Growth factor matters**: doubling is common; some implementations use 1.5× to allow
reuse of freed blocks. **Reserve capacity when you know the size** — repeated reallocation
and copying is a common invisible cost.

---
