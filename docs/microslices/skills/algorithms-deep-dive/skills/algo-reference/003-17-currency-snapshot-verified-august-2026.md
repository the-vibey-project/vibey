---
id: skill-17-currency-snapshot-verified-august-2026-37e644c50e
purpose: 17 currency snapshot verified august 2026
source: src/vibey_tools/skills/plugins/algorithms-deep-dive/skills/algo-reference/SKILL.md
requires: ["skill-16-contested-questions-cd5eef5285"]
links: ["skill-18-the-canon-46b017ee1d"]
---

## §17. Currency Snapshot — verified August 2026

**[DURABLE] Read this section knowing that most of this document does not move.** Quicksort
is 1961, B-trees 1970, Dijkstra 1959, Bloom filters 1970. What follows is what genuinely
changed.

| Thing | Status as of Aug 2026 | Decay risk |
|---|---|---|
| **⚠️ Optimal open addressing** | **January 2025: Farach-Colton, Krapivin & Kuszmaul, "Optimal Bounds for Open Addressing Without Reordering" (arXiv 2501.02305), disproving the central conjecture of Yao's "Uniform Hashing is Optimal" (1985).** **Funnel hashing** (greedy): **O(log² δ⁻¹)** worst-case expected probes, refuting Yao's Ω(δ⁻¹) claim. **Elastic hashing** (non-greedy): **O(1) amortized expected**, **O(log δ⁻¹) worst-case expected**, without reordering. **All results have matching lower bounds.** ⚠️ **CACM's caveats: disproves Yao's conjectures but not Ullman's; some non-open-addressing designs (Iceberg tables) are faster; the construction covers insertions only, not deletions.** Authors "take a lower-key view" than the coverage did | Low (theorem) |
| **Rust standard-library sorts** | **driftsort** (stable, from glidesort) and **ipnsort** (unstable) merged 2024. Reported: **ipnsort up to ~2.4× faster on random inputs**; **driftsort up to ~17× on low-cardinality patterns (random_d20)**. ⚠️ Both **prefer ILP over SIMD** for cross-architecture adaptability, and both minimize **i-cache misses** — a factor instruction-count analysis misses. `sort_unstable` documents **linear time on sorted and reversed inputs**, **O(n log k)** for k distinct elements | Medium |
| **Sorting landscape generally** | **pdqsort** is the widely-adopted branchless-partitioning baseline (Rust, and ported into other ecosystems including a Dart `package:collection` proposal). **fluxsort/crumsort** ideas were adopted into crumsort-rs, glidesort, ipnsort, driftsort. **Powersort** (provably near-optimal merge policy) adopted in CPython | Medium |
| **Swiss tables** | `absl::flat_hash_map` and Rust's `hashbrown`-backed `HashMap` — SIMD-scanned control bytes over open addressing. Current practical state of the art | Low |
| **Vector search: indexes** | **HNSW** the in-memory default; **IVF** for billion-scale partitioning; **DiskANN/Vamana** — SSD-resident index + PQ vectors in RAM, indexing **1B+ vectors on one machine with ~64 GB RAM**, ~95%+ recall@1 at sub-5ms on SIFT-1B; **ScaNN** (anisotropic quantization); **CAGRA** (GPU). Reported 2026 scaling: **DiskANN to ~4.8B vectors on a single server** with GPU-accelerated build via NVIDIA cuVS | **High** |
| **Vector search: quantization** | **PQ (typically 16–32× compression), scalar, binary, RaBitQ.** Quantize-then-rerank is the standard production pattern. Binary quantization reported in Elasticsearch with large cost/indexing-speed gains | **High** |
| **⚠️ Filtered ANN** | **The live problem.** Post-filtering loses results or over-fetches; pre-filtering needs a linearly-growing mask; **heavy filtering disconnects the HNSW graph → recall cliff.** Active line of work: **Filtered-DiskANN** (reported order-of-magnitude gains over IVF/HNSW/NHQ/Milvus baselines, recall near 100% at specificity down to 10⁻⁴–10⁻⁶), **ACORN**, **CAPS**, vendor filterable-HNSW designs. **Benchmarks are usually unfiltered — test this yourself** | **High** |
| **ANN benchmarking** | **ANN-Benchmarks** remains the standard containerized harness; **VIBE** (2025) added an embeddings-focused benchmark; **big-ann-benchmarks** covers filtered tracks | Medium |
| **Learned indexes** | Still research-forward; adoption limited relative to attention (§16.4) | Medium |

**Goes stale fastest:** everything in §13.4 → `algo-probabilistic-concurrency-and-measurement` — vector search is moving quarterly.
**Essentially never stale:** §1–§3 → `algo-foundations-and-machine-model`, `algo-data-structures`, §5–§12 → `algo-data-structures`, `algo-core-algorithms`, `algo-probabilistic-concurrency-and-measurement`, §14 → `algo-probabilistic-concurrency-and-measurement`'s principles, §15.

---
