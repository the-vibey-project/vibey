---
id: skill-6-heaps-and-priority-queues-b0c0aaaba3
purpose: 6 heaps and priority queues
source: src/vibey_tools/skills/plugins/algorithms-deep-dive/skills/algo-data-structures/SKILL.md
requires: ["skill-5-trees-and-ordered-structures-804ed6ec93"]
links: []
---

## §6. Heaps and Priority Queues

**[DURABLE] The binary heap is one of the best cost/benefit structures in computing**:
an implicit tree in a flat array, so no pointers and good locality. O(log n) push/pop,
**O(1) peek**, and **O(n) heapify** (not O(n log n) — a common misconception).

**Uses**: scheduling, Dijkstra and A\*, top-k, merging sorted streams, timer wheels,
event simulation.

**Variants worth knowing**: **d-ary heaps** (shallower, better cache, faster decrease-key —
often a real win for Dijkstra), **pairing heaps** (good practical decrease-key),
**Fibonacci heaps** (⚠️ **theoretically superior and practically slower** — the canonical
example of an algorithm whose constants defeat its asymptotics), **binomial** and
**leftist heaps** for mergeability.

**⚠️ For top-k, a bounded min-heap of size k is O(n log k)** and usually beats sorting.
And for a **fixed small range of priorities, a bucket queue is O(1)** and beats any
comparison heap.
