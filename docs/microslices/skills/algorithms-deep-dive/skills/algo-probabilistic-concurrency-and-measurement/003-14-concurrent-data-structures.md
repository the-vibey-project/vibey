---
id: skill-14-concurrent-data-structures-268be5c9fa
purpose: 14 concurrent data structures
source: src/vibey_tools/skills/plugins/algorithms-deep-dive/skills/algo-probabilistic-concurrency-and-measurement/SKILL.md
requires: ["skill-13-measurement-b3c762c39f"]
links: []
---

## §14. Concurrent Data Structures

**[DURABLE] Concurrency changes every answer in this document**, and the ordering of the
options below is the recommended order of preference.

```
1. DON'T SHARE           Partition the data. Thread-local, sharded, actor-per-key.
                         ⚠️ Almost always the right answer and the least explored one
2. IMMUTABLE / PERSISTENT  Structural sharing; readers never block. Great for read-heavy
3. COARSE LOCK           A single mutex. Boring, correct, and fast enough far more often
                         than people assume. START HERE and measure
4. FINE-GRAINED LOCKS    Striped/sharded locks. ⚠️ Deadlock risk; establish a lock order
5. RW LOCKS              Only when reads massively dominate; ⚠️ writer starvation
6. LOCK-FREE             CAS-based. Hard to get right, harder to debug
7. WAIT-FREE             Bounded steps per operation. Rare, and usually not worth it
```

**Key structures**: **concurrent hash maps** (striped or lock-free — `ConcurrentHashMap`,
`DashMap`), **MPMC/SPSC queues** (⚠️ **SPSC ring buffers are dramatically faster** — use the
most restrictive queue that fits), **the Disruptor** pattern (ring buffer + sequence
barriers; the reference design for low-latency pipelines), **RCU** (read-copy-update —
readers pay nothing), **hazard pointers** and **epoch-based reclamation** for the
memory-reclamation problem, and **CRDTs** for eventually-consistent replicated state.

> **⚠️ GOTCHA — the concurrency-specific failure modes:**
> - **The ABA problem.** A CAS succeeds because the value returned to A, but the structure
>   changed underneath. **The reason hazard pointers and epochs exist.**
> - **Memory reclamation is the hard part of lock-free programming**, not the algorithm.
>   You can't free a node while another thread might read it.
> - **⚠️ False sharing.** Two threads writing *different* variables on the **same cache
>   line** ping-pong that line between cores. **Can cost an order of magnitude, and it is
>   invisible in the source.** Pad to cache-line boundaries.
> - **Memory ordering.** Acquire/release/seq_cst are not decoration. **Getting this wrong
>   produces bugs that appear only on weakly-ordered architectures (ARM) after passing all
>   tests on x86.**
> - **Lock-free ≠ faster.** Under contention it often *is*; under low contention a mutex
>   frequently wins on simplicity and cache behaviour. **Measure.**
