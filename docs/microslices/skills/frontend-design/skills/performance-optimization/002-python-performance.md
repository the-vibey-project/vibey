---
id: skill-python-performance-059ab084a9
purpose: python performance
source: src/vibey_tools/skills/plugins/frontend-design/skills/performance-optimization/SKILL.md
requires: ["skill-core-principle-3f97d4b15f"]
links: ["skill-next-js-typescript-performance-341b4ed557"]
---

## Python Performance

### Profiling Toolkit

| Tool              | Type        | Use for                                                   | Command / Notes                                      |
|-------------------|-------------|-----------------------------------------------------------|------------------------------------------------------|
| `cProfile`        | Deterministic | Whole-program overview, first pass                        | `python -m cProfile -s cumtime app.py`               |
| `line_profiler`   | Deterministic | Per-line timing in hot functions                          | `@profile` decorator; `kernprof -l -v script.py`     |
| `memory_profiler` | Deterministic | Per-line memory                                           | `@profile`; `mprof run`/`mprof plot`                 |
| `py-spy`          | Sampling    | **Production** — attaches to live PID, ~0.1ms overhead, no restart | `py-spy top --pid 1234`; `py-spy record -o out.svg --pid 1234 --duration 30` |
| `Scalene`         | Sampling    | Deep dives — separates Python vs native vs system %, per-line memory, copy-volume detection | `scalene app.py` or `%scalene` in Jupyter; 10–20% overhead |

**Investigation loop:**
1. `py-spy`/`pyinstrument` → find the hot path
2. `Scalene` → classify: Python %? (vectorize/algorithm) native %? (library/IO) memory? (copy volume)
3. `line_profiler` → zoom in on the specific function

**Real case:** `py-spy top` revealed a `copy.deepcopy` in a retry loop; replacing it dropped P99 ~40%.

### The GIL, Threading, and Free-Threading

**GIL behavior:** Only one thread runs Python bytecode at a time.
- **I/O-bound** work → threading works (threads release the GIL while waiting on I/O)
- **CPU-bound** work → use `multiprocessing` / `concurrent.futures.ProcessPoolExecutor`

**Multiprocessing caveat:** Each process has interpreter-creation + data-copy overhead. For small per-task work (e.g., per-row DataFrame operations), multiprocessing can be 2–10x *slower*. Per-task work must be large enough to amortize the cost.

**Free-threaded Python:**

| Version  | Status                                                           |
|----------|------------------------------------------------------------------|
| 3.13     | Phase I — experimental (`python3.13t`); ~40% single-thread penalty |
| 3.14     | Phase II — officially supported, still opt-in (`python3.14t`); "roughly 5–10% single-thread penalty" (official docs); specializing adaptive interpreter enabled |

Phase II status from the Python 3.14 "What's New" docs: "the free-threaded build of Python is now supported and no longer experimental."

**C-extension safety:** If you import a C extension that hasn't declared thread-safety, the interpreter silently re-enables the GIL for the whole process. Check with `sys._is_gil_enabled()` after imports.

**Install:** `uv python install 3.14t` or python.org installers / deadsnakes PPA.

**Real benchmark:** Free-threaded multi-threaded DataFrame row processing cut time ≥50% (sometimes >80%) vs single-thread; multiprocessing on the same small tasks degraded performance.

**Adopt for:** CPU-bound parallel workloads (image processing, transforms, ML inference) once your key dependencies ship free-threaded wheels.

### Faster CPython (3.11 → 3.14)

| Version | Key improvement                                              | Speedup vs. 3.10        |
|---------|--------------------------------------------------------------|-------------------------|
| 3.11    | Specializing adaptive interpreter (PEP 659); zero-cost exceptions; frame optimizations | 1.25x avg; recursive functions 1.7x |
| 3.12    | Refined specialization; per-interpreter GIL groundwork      | —                       |
| 3.13    | Experimental free-threading + experimental JIT (0–5% today) | —                       |
| 3.14    | More aggressive inlining/specialization                      | Cumulatively ~40–50% faster than 3.10 |

**Upgrading the interpreter is one of the highest-ROI changes** — recompile/retest and you get speedups with no code change.

The 3.13 JIT is currently 0–5% — infrastructure for future gains, not a reason to upgrade today.

### NumPy/Pandas Vectorization

**The single biggest per-effort win in data code.**

| Method             | Time (10k rows, element-wise) | Relative          |
|--------------------|-------------------------------|-------------------|
| Vectorized         | ~0.001s                       | 1x (baseline)     |
| `apply()`          | ~0.13s                        | ~100x slower      |
| `iterrows()`       | ~0.74s                        | ~740x slower      |

Why loops are slow: every iteration goes through the Python interpreter with per-object type checks. NumPy pushes the loop into pre-compiled SIMD C operating on homogeneous contiguous memory.

**Rules:**
1. Prefer native vectorized column operations and boolean indexing
2. `df.apply(fn, raw=True)` bypasses Series overhead when you must use `apply`
3. Use `itertuples`, never `iterrows`, if you must loop
4. `np.vectorize` is convenience, not performance — it's a for-loop
5. Drop to `.to_numpy()` for 2x–3000x gains in some cases
6. When not vectorizable, use Numba

**Memory:** choose smallest dtypes, use categoricals for low-cardinality strings, prefer `float32`, store data as Parquet.

### Compilation and Acceleration

| Tool    | Best for                                              | Benchmark                                   | Limitation                              |
|---------|-------------------------------------------------------|---------------------------------------------|-----------------------------------------|
| Numba `@njit` | Numeric Python/NumPy with minimal code change   | Pairwise distance: pure Python 13,400ms → NumPy 111ms → Numba **9.12ms** (Numba/Cython ~1300–1500x over pure Python, ~10x over NumPy) | Only numeric/NumPy-compatible code; no arbitrary Python objects |
| Cython  | Distributable libraries, typed memoryviews, C calls  | ~9.87ms (similar to Numba); Numba beat Cython 20–300% in some loop cases | More effort; needs static typing to shine |
| PyPy    | Long-running pure-Python loop-heavy code after warmup | Good | Weaker C-extension compat; larger footprint; not for short scripts |
| ctypes/cffi | Calling existing C libraries                    | —                                           | Need an existing compiled library       |

**Caveat:** Cython/Numba still pay Python↔native conversion overhead at call boundaries. Best after profiling identifies a small hot set of functions.

### Asyncio Best Practices

**`asyncio.gather` vs `asyncio.TaskGroup`:**
- `gather` runs concurrently but does NOT cancel siblings on failure
- `TaskGroup` (3.11+) gives structured concurrency: any task failure cancels the rest and raises `ExceptionGroup` (handle with `except*`)

**Always set timeouts on every external call.**

**Antipatterns:**
1. **Blocking the event loop** with CPU-bound code or sync I/O (`time.sleep`, `json.loads` on huge strings, sync DB drivers) — offload with `await loop.run_in_executor(pool, fn)` or `asyncio.to_thread`
2. **Un-awaited tasks getting GC'd** — the event loop holds only weak refs; collect tasks in a `set` and `add_done_callback(s.discard)`
3. **Sharing asyncio objects across threads**

The eager task factory (`asyncio.eager_task_factory`) can speed async-heavy `gather`/`TaskGroup` workloads (up to ~50% in some cases).

### ASGI vs. WSGI

WSGI (Flask/classic Django): one request per worker; a worker blocks while waiting on DB/IO.

ASGI (FastAPI/Starlette, Django async): asyncio event loop — one Uvicorn worker handles thousands of concurrent in-flight I/O-bound requests.

**Benchmarks (Python 3.13, single vCPU, I/O-bound):**

| Scenario                        | FastAPI       | Flask           |
|---------------------------------|---------------|-----------------|
| Auth + DB/JSON endpoint         | ~435 RPS      | ~315–344 RPS    |
| Plaintext                       | ~22,000 RPS   | ~3,200 RPS      |
| Async SQLAlchemy + Postgres      | ~8,200 RPS    | ~1,900 RPS      |

FastAPI is generally ~3x+ Flask on I/O-bound concurrency. Real apps with business logic compress these gaps. For CPU-bound or simple sync apps the async advantage shrinks.

### Database from Python

- Use SQLAlchemy connection pooling (avoid per-request connects)
- Batch queries to avoid N+1
- Use `selectinload`/`joinedload` for eager loading
- Use async drivers (asyncpg) under ASGI

---
