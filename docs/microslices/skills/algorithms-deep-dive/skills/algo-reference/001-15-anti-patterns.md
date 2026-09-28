---
id: skill-15-anti-patterns-7cb55564be
purpose: 15 anti patterns
source: src/vibey_tools/skills/plugins/algorithms-deep-dive/skills/algo-reference/SKILL.md
requires: []
links: ["skill-16-contested-questions-cd5eef5285"]
---

## §15. Anti-Patterns

| Anti-pattern | Why |
|---|---|
| Choosing by asymptotics alone | **The constant spans two orders of magnitude and is set by memory layout** (§2 → `algo-foundations-and-machine-model`) |
| Linked list as the default sequence | One cache miss per node; arrays win to surprisingly large n (§3 → `algo-data-structures`) |
| Optimizing without profiling | The hot spot is rarely where you think (§13 → `algo-probabilistic-concurrency-and-measurement`) |
| Benchmarking at one input size | ⚠️ **Cache cliffs make this actively misleading** (§2.1 → `algo-foundations-and-machine-model`, §13 → `algo-probabilistic-concurrency-and-measurement`) |
| Benchmarking without a black-box hint | The compiler deletes your benchmark (§13 → `algo-probabilistic-concurrency-and-measurement`) |
| Reporting mean latency | Hides the tail your users experience. p50/p95/p99 (§13 → `algo-probabilistic-concurrency-and-measurement`) |
| Hash map when you need ordered iteration or ranges | Wrong structure class (§4 → `algo-data-structures` vs §5 → `algo-data-structures`) |
| Tree when you only do point lookups | Strictly worse than a hash map (§5.1 → `algo-data-structures`) |
| Not pre-sizing a collection you can size | Repeated reallocation, and a resize latency spike (§3 → `algo-data-structures`, §4.2 → `algo-data-structures`) |
| Weak/predictable hash on untrusted keys | ⚠️ **Hash-flooding DoS** (§4.2 → `algo-data-structures`) |
| Depending on hash map iteration order | Unordered by definition, randomized in some languages (§4.2 → `algo-data-structures`) |
| Mutating a key after insertion | Silently corrupts the table (§4.2 → `algo-data-structures`) |
| Comparator that isn't a strict weak ordering | ⚠️ **UB — can crash or corrupt memory** (§7.2 → `algo-core-algorithms`) |
| Sorting to get the top k | Heap is O(n log k) (§6 → `algo-data-structures`) |
| Sorting to get one element | Quickselect is O(n) average (§7.2 → `algo-core-algorithms`) |
| Assuming Fibonacci heaps are faster | **The canonical constants-defeat-asymptotics case** (§6 → `algo-data-structures`) |
| Dijkstra with negative edges | ⚠️ **Silently wrong, not an error** (§9 → `algo-core-algorithms`) |
| Recursive DFS on a large graph | Stack overflow. Explicit stack (§9 → `algo-core-algorithms`) |
| Adjacency matrix for a sparse graph | O(V²) space for nothing (§9 → `algo-core-algorithms`) |
| Greedy without proving the exchange argument | ⚠️ Silently suboptimal (§11.2 → `algo-core-algorithms`) |
| DP table storing all rows when two suffice | Often the cache-fit difference (§11.1 → `algo-core-algorithms`) |
| Treating amortized O(1) as per-operation O(1) | ⚠️ **This is your p99** (§11.4 → `algo-core-algorithms`) |
| Exact counting when an estimate would do | HLL is kilobytes for billions (§12 → `algo-probabilistic-concurrency-and-measurement`) |
| Deploying a sketch without knowing the error model | Fine for a dashboard, not for billing (§12 → `algo-probabilistic-concurrency-and-measurement`) |
| Reimplementing binary search | ⚠️ The JDK shipped an overflow bug for years (§8 → `algo-core-algorithms`) |
| Hand-rolling string search | SIMD `memmem` beats naive KMP (§10 → `algo-core-algorithms`) |
| Treating strings as arrays of characters | Unicode: graphemes ≠ code points ≠ bytes (§10 → `algo-core-algorithms`) |
| k-d tree for high-dimensional similarity | ⚠️ Degrades above ~20 dims (§8 → `algo-core-algorithms`, §13.4 → `algo-probabilistic-concurrency-and-measurement`) |
| Evaluating a vector store on unfiltered benchmarks | **Filtered search is where they fall over** (§13.4 → `algo-probabilistic-concurrency-and-measurement`) |
| Reaching for lock-free first | Try not-sharing, then a mutex, then measure (§14 → `algo-probabilistic-concurrency-and-measurement`) |
| Ignoring false sharing | ⚠️ **Order-of-magnitude cost, invisible in source** (§14 → `algo-probabilistic-concurrency-and-measurement`) |
| Testing concurrent code only on x86 | Memory-ordering bugs surface on ARM (§14 → `algo-probabilistic-concurrency-and-measurement`) |
| Rewriting your hash map because of a 2025 paper | ⚠️ Insertions only, and not the bottleneck (§4.3 → `algo-data-structures`) |

---
