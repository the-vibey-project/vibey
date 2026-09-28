---
id: skill-9-graphs-501de76684
purpose: 9 graphs
source: src/vibey_tools/skills/plugins/algorithms-deep-dive/skills/algo-core-algorithms/SKILL.md
requires: ["skill-8-searching-and-indexing-aad33f628c"]
links: ["skill-10-strings-and-text-3706ed1403"]
---

## §9. Graphs

**[DURABLE] Representation is the first decision and it's usually adjacency lists** —
adjacency matrices cost O(V²) space and only win for genuinely dense graphs or when you
need O(1) edge existence checks. **CSR (compressed sparse row)** is the cache-friendly
static form and is what serious graph processing uses.

**The traversals**: **BFS** (shortest path in *unweighted* graphs, level order),
**DFS** (cycle detection, topological sort, SCC, backtracking — ⚠️ **use an explicit stack
in production**; recursion depth on a large graph is a stack overflow).

**Shortest paths, and picking the right one:**

| Algorithm | Use | Complexity |
|---|---|---|
| **BFS** | Unweighted | O(V+E) |
| **Dijkstra** | Non-negative weights | O((V+E) log V) with a heap |
| **A\*** | Single target with a good heuristic | Dijkstra + admissible heuristic |
| **Bellman-Ford** | ⚠️ **Negative weights**; detects negative cycles | O(VE) |
| **Floyd-Warshall** | All pairs, small dense graphs | O(V³) |
| **Bidirectional search** | Point-to-point on large graphs | Often dramatically better |

**⚠️ Dijkstra silently gives wrong answers with negative edges.** It doesn't error; it
returns a plausible wrong path. Know which one you need.

**Also**: **topological sort** (build systems, task scheduling, dependency resolution —
and cycle detection is the same algorithm), **union-find** for connectivity and Kruskal's,
**Prim's** for MST, **max-flow/min-cut** (Dinic's in practice; the reduction target for a
surprising number of assignment and matching problems), **bipartite matching**,
**PageRank** and centrality, and **community detection**.

**[DURABLE] Recognizing that your problem is a graph problem is most of the work.**
Dependency resolution, permissions inheritance, routing, scheduling, deduplication,
recommendation, and data lineage are all graph problems wearing business costumes.

---
