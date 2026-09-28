---
id: skill-11-performance-and-parallelism-36e18650e2
purpose: 11 performance and parallelism
source: src/vibey_tools/skills/plugins/math-science-programming/skills/sci-statistics-performance-and-reproducibility/SKILL.md
requires: ["skill-10-statistics-and-uncertainty-b70b7cd8ad"]
links: ["skill-12-data-i-o-and-units-4adaa9e87b"]
---

## §11. Performance and Parallelism

**[DURABLE] The order of operations, and doing it in a different order wastes weeks:**
```
1. Make it correct                        (§13)
2. Profile — find where the time is       ⚠️ never guess
3. Better algorithm / better library      ← the biggest wins live here
4. Vectorize; use Level-3 BLAS shapes     (§3)
5. Memory layout and cache behaviour
6. Parallelize on one node (threads)
7. GPU, if the problem suits it
8. Distributed (MPI), if it must
```

**⚠️ Most numerical code is memory-bandwidth-bound, not compute-bound.** The **roofline
model** is the right mental tool: plot arithmetic intensity (FLOPs per byte moved) against
achievable performance and you can see immediately whether you're near the bandwidth
ceiling or the compute ceiling. **BLAS Level 1 and 2 operations, and most stencil codes,
are bandwidth-bound** — which means micro-optimizing the arithmetic achieves nothing.

**The parallel toolkit**: **OpenMP** (shared memory, incremental), **MPI** (⚠️ **still the
backbone of HPC, and not going anywhere**), **CUDA/HIP/SYCL** for GPUs, **Kokkos** and
**RAJA** for performance portability, **Dask**/**Ray** for Python-level distribution, and
**Numba**/**JAX**/**Cython** for compiling Python hot paths.

> **⚠️ GOTCHA — parallel numerics has its own failure modes:**
> - **⚠️ Non-associativity means results change with thread count** (§1.1 → `sci-floating-point-and-numerical-foundations`). **This is not a
>   bug, and it will look like one.** If you need bit-reproducibility, you need
>   deterministic reduction orders — Intel MKL offers "conditional numerical
>   reproducibility" by fixing instruction sets and requiring consistent thread counts,
>   ⚠️ **at a performance cost**.
> - **False sharing** — threads writing adjacent memory ping-pong cache lines.
> - **Load imbalance** — the slowest rank sets your runtime.
> - **Communication cost** — ⚠️ **an all-reduce at every timestep will dominate**; overlap
>   communication with computation.
> - **Amdahl's law** — the serial fraction bounds everything.
> - **⚠️ Silent data corruption** at scale is real in large HPC runs, and it's why
>   checkpointing and consistency checks matter.

---
