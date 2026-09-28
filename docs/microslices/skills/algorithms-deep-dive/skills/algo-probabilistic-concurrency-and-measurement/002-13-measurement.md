---
id: skill-13-measurement-b3c762c39f
purpose: 13 measurement
source: src/vibey_tools/skills/plugins/algorithms-deep-dive/skills/algo-probabilistic-concurrency-and-measurement/SKILL.md
requires: ["skill-12-probabilistic-and-streaming-structures-71c65da736"]
links: ["skill-14-concurrent-data-structures-268be5c9fa"]
---

## §13. Measurement

**[DURABLE] The discipline that separates real optimization from folklore**, and the part
most engineers skip.

**Profile first.** Intuition about where time goes is unreliable, and the hot spot is
usually not where you'd guess. **Amdahl's law**: optimizing 10% of runtime by 10× gains
you 9%.

**Benchmarking correctly:**
- **Realistic data, realistic distribution, realistic size** — and **benchmark across
  sizes**, because §2.1 → `algo-foundations-and-machine-model`'s cache cliffs make single-size benchmarks actively misleading.
- **Warm up** (JIT, caches, branch predictors), then **measure many iterations**.
- **⚠️ Prevent dead-code elimination** — the compiler will delete your benchmark if the
  result is unused. Use the black-box/`std::hint::black_box` facility your language
  provides.
- **Report distributions, not means.** p50/p95/p99 and variance. **A mean hides the tail
  that your users experience.**
- **Control the environment**: pin CPUs, disable turbo/frequency scaling if you can, and
  run enough samples to see the noise floor.
- **Use a real harness** — Criterion, JMH, `google/benchmark`, `pytest-benchmark`,
  `hyperfine`. Hand-rolled timing loops get all of the above wrong.
- **Measure hardware counters** when it matters: `perf stat` gives cache misses, branch
  mispredicts, and IPC, which turns "it's slow" into "it's memory-bound."

### 13.4 Vector and similarity search

**[VERSIONED] Worth its own subsection because it went from research to standard
infrastructure in about four years**, driven by embeddings and RAG.

**The problem**: nearest-neighbour in high dimensions, where **k-d trees fail** (§8 → `algo-core-algorithms`) and
exact search is a linear scan. **The answer is approximate (ANN), trading recall for
speed.**

| Approach | Notes |
|---|---|
| **HNSW** | Hierarchical navigable small world graphs. **The in-memory default.** Excellent recall/QPS; ⚠️ **memory-hungry — the whole index in RAM** |
| **IVF** | Partition via k-means, search `nprobe` nearest cells. Scales better to billions; needs `nlist`/`nprobe` tuning |
| **DiskANN (Vamana)** | **Index and full-precision vectors on SSD, PQ-compressed vectors in RAM** for routing, then rerank. Indexes 1B+ vectors on a single machine with ~64 GB RAM |
| **ScaNN** | Anisotropic quantization — optimizes directional accuracy rather than reconstruction error; strong for inner-product search |
| **CAGRA** | GPU-oriented graph index |

**Quantization is the other axis**: **PQ** (product quantization — typically 16–32× smaller),
**scalar**, **binary**, and **RaBitQ**. **⚠️ Nearly all production deployments quantize and
rerank**, because storing full-precision vectors in RAM at scale is the dominant cost.

> **⚠️ GOTCHA — filtered search is where naive implementations fall over, and it's what
> real applications need.** "Find similar documents *where tenant = X and date > Y*" breaks
> the graph assumptions. **Post-filtering** either loses results or requires
> over-fetching; **pre-filtering** needs a mask that grows linearly with the dataset. And
> **when too many vectors are filtered out, an HNSW graph becomes disconnected and recall
> collapses** — the "recall cliff." This drove a whole line of work (Filtered-DiskANN,
> ACORN, and vendor-specific filterable-HNSW designs) and **it is the first thing to test
> when evaluating a vector store**, because benchmark numbers are almost always unfiltered.

**[DURABLE] Benchmark on your own data.** ANN performance is extremely dataset-dependent —
dimensionality, intrinsic dimension, and clustering all matter more than the published
QPS-vs-recall curve. **ANN-Benchmarks** and **VIBE** are the standard harnesses; use them
as method, not as an answer.

---
