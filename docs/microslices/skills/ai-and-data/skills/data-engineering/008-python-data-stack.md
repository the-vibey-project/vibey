---
id: skill-python-data-stack-328ad25db7
purpose: python data stack
source: src/vibey_tools/skills/plugins/ai-and-data/skills/data-engineering/SKILL.md
requires: ["skill-data-quality-layered-approach-625fecd953"]
links: ["skill-data-quality-at-scale-pydantic-vs-pandera-b3273d4bd2"]
---

## Python Data Stack

### pandas
- Optimize memory: categorical dtypes for low-cardinality strings, downcast numerics, chunk large CSVs (`chunksize`), Arrow-backed dtypes (pandas 2.x)
- Avoid row-wise `apply`/`iterrows` — vectorize
- Single-threaded for most ops (GIL-bound)

### Polars (Rust-based, columnar Arrow)
- Multi-threaded by default
- **Lazy API**: predicate pushdown, projection pruning, operation fusion, streaming mode for larger-than-RAM data
- Benchmarks vs pandas (NYC taxi 12.7M rows): 25× faster CSV reads, 5–10× faster aggregations, joins up to ~13.75×
- 650GB Delta test on 32GB EC2: Polars 12 min vs PySpark >1 hour
- Parquet write performance converges (both delegate to PyArrow C++)

### DuckDB (in-process OLAP)
- Vectorized execution; reads Parquet/S3 directly with columnar pushdown
- 1M-row query: ~3.84s vs pandas' ~19.57s
- 5–10× faster group-bys on >100M rows
- Best for local/embedded analytics and as a dbt/test backend

### PySpark
- Use DataFrame API (Catalyst optimizer) over RDDs
- Avoid data skew (salting, AQE); prefer broadcast joins when one side fits in memory
- **Only reach for Spark when data won't fit on a single node** or you need distributed/streaming/MLlib

### Arrow/PyArrow
Zero-copy columnar IPC — the lingua franca between Polars, DuckDB, pandas 2.x, and Spark.

---
