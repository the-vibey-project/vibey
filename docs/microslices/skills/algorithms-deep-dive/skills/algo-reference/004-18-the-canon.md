---
id: skill-18-the-canon-46b017ee1d
purpose: 18 the canon
source: src/vibey_tools/skills/plugins/algorithms-deep-dive/skills/algo-reference/SKILL.md
requires: ["skill-17-currency-snapshot-verified-august-2026-37e644c50e"]
links: ["skill-19-quick-reference-868ab365c5"]
---

## §18. The Canon

### 18.1 Books

| Author | Work | Why |
|---|---|---|
| **Cormen, Leiserson, Rivest & Stein** | ***Introduction to Algorithms*** (CLRS) | The reference. Comprehensive, rigorous, not a tutorial |
| **Sedgewick & Wayne** | ***Algorithms***, 4th ed. | **The best learning book** — implementations you can read, excellent site and course |
| **Kleinberg & Tardos** | *Algorithm Design* | **The best on *recognizing* which technique applies** — the actual skill |
| **Skiena** | ***The Algorithm Design Manual*** | ⚠️ **The most practical of the lot.** Part 2 is a catalogue: "I have this problem, what do I use?" |
| **Bentley** | ***Programming Pearls*** | Short, old, and still the best writing on algorithm engineering and measurement |
| **Knuth** | *TAOCP* | Monumental. A reference to consult, not to read through |
| **Demaine / Erik & Martin** | *Advanced Data Structures* (MIT OCW) | For the exotic structures |
| **Fog, Agner** | *Optimization manuals* (free) | §2 → `algo-foundations-and-machine-model` in exhaustive detail. **The reference for what the hardware does** |
| **Herlihy & Shavit** | ***The Art of Multiprocessor Programming*** | §14 → `algo-probabilistic-concurrency-and-measurement`, and the standard |
| **Kleppmann** | *Designing Data-Intensive Applications* | ⚠️ **The best treatment of §5.2 → `algo-data-structures`'s B-tree/LSM trade-off in context** |
| **Petrov** | *Database Internals* | Storage structures in depth |
| **Roughgarden** | *Algorithms Illuminated* (4 vols) | Clear, well-paced, with a good companion course |
| **Okasaki** | *Purely Functional Data Structures* | Persistent/immutable structures; underlies §14 → `algo-probabilistic-concurrency-and-measurement`'s option 2 |

### 18.2 People and sources
**Sedgewick** and **Roughgarden** (courses), **Erik Demaine** (MIT 6.006/6.851 lectures —
outstanding), **Daniel Lemire** (SIMD, fast parsing, `simdjson` — **the best public writing
on measured algorithm engineering**), **Andrei Alexandrescu** ("Speed Is Found In The
Minds of People"), **Chandler Carruth** (CppCon talks on data structures and hardware),
**Martin Thompson** (mechanical sympathy, the Disruptor), **Orson Peters** (pdqsort,
glidesort), **Lukas Bergdoll** (`sort-research-rs` — genuinely rigorous sort benchmarking),
**Martín Farach-Colton** and **William Kuszmaul** (§4.3 → `algo-data-structures`), **Quanta Magazine** for
accessible coverage of results like §4.3 → `algo-data-structures`'s.

**Practical**: **`sort-research-rs`** (the benchmark suite behind §7.1 → `algo-core-algorithms`), **ANN-Benchmarks**
and **VIBE** (§13.4 → `algo-probabilistic-concurrency-and-measurement`), **Google Benchmark / Criterion / JMH / hyperfine**, **`perf`** and
**Godbolt**, **Big-O Cheat Sheet** (with §2 → `algo-foundations-and-machine-model`'s caveat firmly in mind), and **VisuAlgo** for
building intuition.

---
