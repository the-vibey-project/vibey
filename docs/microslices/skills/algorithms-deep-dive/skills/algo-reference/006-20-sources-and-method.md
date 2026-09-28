---
id: skill-20-sources-and-method-58e15c6df3
purpose: 20 sources and method
source: src/vibey_tools/skills/plugins/algorithms-deep-dive/skills/algo-reference/SKILL.md
requires: ["skill-19-quick-reference-868ab365c5"]
links: []
---

## §20. Sources and Method

**Method.** Narrative review, written as **selection and engineering guidance** rather than
as a course, and deliberately complementary to a theory-of-computation reference — this
document assumes the question "is it tractable" is settled and addresses "which one, and
why is it slow." **The great majority of the material is textbook-stable**: the structures
and algorithms in §3–§12 → `algo-data-structures`, `algo-core-algorithms`, `algo-probabilistic-concurrency-and-measurement` date from the 1950s–1990s and the trade-offs among them have not
changed. §2 → `algo-foundations-and-machine-model`'s hardware model reflects behaviour that has been broadly stable since roughly
2010; the specific cycle counts are order-of-magnitude figures that vary by
microarchitecture and should be treated as such. Three targeted searches were run in
**August 2026** on the areas where movement was plausible — theoretical hashing results,
modern sort implementations, and vector search. **The rest was not "verified" against web
sources because CLRS, Skiena, Sedgewick, and the primary literature are the authority and
they are stable.**

**Search log** (August 2026): Krapivin/Farach-Colton/Kuszmaul open-addressing result and
its reception · Rust driftsort/ipnsort and the modern sorting landscape · HNSW/DiskANN,
quantization, and filtered ANN search.

**Primary and near-primary sources consulted (selected):**
- **arXiv 2501.02305**, *"Optimal Bounds for Open Addressing Without Reordering"*
  (Farach-Colton, Krapivin, Kuszmaul), read directly for the bounds and the scope of the
  claim; **CACM's "Speeding Up Hash Tables"** for the expert caveats (Ullman's conjecture,
  Iceberg tables, insertions-only); **Quanta** for the accessible account
- **`Voultapher/sort-research-rs`** — the driftsort and ipnsort design write-ups, which are
  the primary source for the ILP-over-SIMD and i-cache reasoning; **Rust standard library
  documentation** for the documented complexity guarantees
- **Vector search**: the **DiskANN/Vamana** line (Subramanya et al., NeurIPS 2019) and
  **Filtered-DiskANN** (WWW 2023) for the filtered-search results; **ANN-Benchmarks**
  (Aumüller, Bernhardsson, Faithfull) and **VIBE** (2025) as the benchmark harnesses;
  **Qdrant's** benchmark documentation for the pre/post-filtering failure analysis; 2026
  survey and systems papers on filtered ANN and quantization

**Confidence statement.** **Very high confidence** in §1–§12 → `algo-foundations-and-machine-model`, `algo-data-structures`, `algo-core-algorithms`, `algo-probabilistic-concurrency-and-measurement` and §14 → `algo-probabilistic-concurrency-and-measurement`'s principles — these
rest on the standard literature and decades of consistent engineering practice, not on
anything I searched. **High confidence** in §4.3 → `algo-data-structures`'s bounds and §7.1 → `algo-core-algorithms`'s Rust design rationale,
both read from primary sources. **Moderate confidence** in the specific performance
multipliers quoted in §17 — the sort speedups are the implementers' own benchmark figures
on their chosen patterns and hardware, and **speedup claims of this kind are always
workload-specific**; treat them as directional. **Lower confidence in §13.4 → `algo-probabilistic-concurrency-and-measurement`'s vector-search
landscape**, which is the fastest-moving material here: several figures come from vendor
blogs and single-system papers with obvious incentives, benchmark methodology varies
enormously across sources, and the field is moving quarterly — **which is exactly why the
section's actual advice is "benchmark on your own data with your own filters" rather than
any ranking.** §2 → `algo-foundations-and-machine-model`'s cycle counts are approximations for reasoning, not measurements for
your machine.
