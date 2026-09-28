---
id: skill-7-sorting-596359c307
purpose: 7 sorting
source: src/vibey_tools/skills/plugins/algorithms-deep-dive/skills/algo-core-algorithms/SKILL.md
requires: []
links: ["skill-8-searching-and-indexing-aad33f628c"]
---

## §7. Sorting

### 7.1 What your library actually does

**[DURABLE] Nobody ships a textbook sort.** Every serious standard library uses a hybrid,
and knowing which one tells you its behaviour.

| Family | Where |
|---|---|
| **Introsort** — quicksort + heapsort fallback + insertion sort for small runs | C++ `std::sort`, historically |
| **pdqsort** (pattern-defeating quicksort) | Adds **branchless partitioning**, pattern detection, and adversarial-input handling. Widely adopted |
| **Timsort** — adaptive natural mergesort | Python `sorted`, Java objects, **stable**, exploits existing runs |
| **Powersort** — Timsort with provably near-optimal merge policy | Adopted in CPython |
| **Radix / counting sort** — non-comparison, O(n·k) | Fixed-width keys; ⚠️ genuinely faster when applicable |

**[VERSIONED] The current state of the art is worth knowing as a concrete example of §2 → `algo-foundations-and-machine-model` in
action.** Rust's standard library replaced its sorts in 2024 with **driftsort** (stable,
derived from glidesort) and **ipnsort** (unstable). Reported gains: **ipnsort up to ~2.4×
faster on random inputs**; **driftsort up to ~17× faster on low-cardinality patterns**.

**⚠️ The design choices are the instructive part**: both **prefer instruction-level
parallelism over SIMD** — because ILP generalizes across architectures and data types while
SIMD depends on specific vector instruction sets — and both are **optimized to minimize
i-cache misses**, a factor automated instruction-count analysis doesn't capture. Rust's
`sort_unstable` documents that ipnsort **achieves linear time on fully sorted and reversed
inputs**, and **O(n log k) on inputs with k distinct elements**.

### 7.2 Choosing

```
Need stability?          → stable sort (Timsort/driftsort/std::stable_sort)
Fixed-width integer keys → radix sort can beat comparison sorting outright
Nearly sorted data       → adaptive sorts (Timsort family) approach O(n)
Small n (< ~20)          → insertion sort. This is what hybrids do internally
Top-k only               → heap, O(n log k). Don't sort (§6)
k-th element only        → quickselect, O(n) average (introselect for worst case)
Larger than memory       → external merge sort
Sort key expensive       → decorate-sort-undecorate (Schwartzian transform)
```

**[DURABLE] The comparison lower bound is Ω(n log n)** — and **radix sort doesn't violate
it**, because it isn't comparison-based. That distinction is worth being precise about.

**⚠️ Comparator correctness is a real production bug source.** Your comparator must define
a **strict weak ordering** — irreflexive, antisymmetric, transitive, with transitive
incomparability. Violating it is undefined behaviour and **can crash or corrupt memory in
C++**; Rust's `sort_unstable` documents that it "may panic if `Ord` does not implement a
total order." **NaN in a float comparator is the classic trigger.**

---
