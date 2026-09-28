---
id: skill-9-performance-9943efcadf
purpose: 9 performance
source: src/vibey_tools/skills/plugins/assembly-programming/skills/assembly-toolchain-performance-and-simd/SKILL.md
requires: ["skill-8-reading-disassembly-d0b146299d"]
links: ["skill-10-simd-and-vector-47c839c4b7"]
---

## §9. Performance

### 9.1 The mental model that's actually right

**[DURABLE] A modern core is a dataflow machine wearing a sequential ISA.** It fetches
many instructions ahead, renames away false dependencies, and executes whatever is ready.
So:

**What costs you, in descending order:**
1. **Cache misses.** ~4 cycles L1, ~12 L2, ~40 L3, **~200–300+ cycles DRAM.** A single
   main-memory miss costs more than a hundred arithmetic instructions. **Memory layout is
   the optimization.**
2. **Branch mispredictions.** ~15–20 cycles of wasted work. Predictable branches are nearly
   free; unpredictable ones are catastrophic — which is why `cmov`/`csel` exists.
3. **The critical dependency chain.** If each iteration depends on the last, you get
   latency, not throughput. **Break the chain with multiple accumulators.**
4. **Long-latency instructions**: division (20–100 cycles), some transcendentals, `pdep`
   on the wrong microarchitecture.
5. **Port contention / execution-unit throughput.**
6. Instruction count. Last.

### 9.2 Latency vs. throughput — the distinction beginners miss

**Latency** = cycles until the result is available to a dependent instruction.
**Throughput** (reciprocal throughput) = cycles between issuing independent instances.

A multiply might be **latency 4, throughput 0.5** — four cycles to get an answer, but you
can start two per cycle. So:
```asm
; SLOW: one accumulator, serialized on the add's latency
.loop:  add rax, [rsi + rcx*8]
        inc rcx
        jne .loop

; FAST: four accumulators, four independent chains, saturates the ports
.loop:  add rax, [rsi + rcx*8]
        add rbx, [rsi + rcx*8 + 8]
        add r8,  [rsi + rcx*8 + 16]
        add r9,  [rsi + rcx*8 + 24]
        add rcx, 4
        jne .loop
        ; then combine rax+rbx+r8+r9
```
**[DURABLE] This "multiple accumulators to break the dependency chain" pattern is the
single most reusable optimization in hand-written assembly**, and it applies identically to
scalar and SIMD code.

**Get the numbers from**: **Agner Fog's instruction tables** (the canonical reference for
x86 latency/throughput/ports across every microarchitecture), **uops.info** (automated and
exhaustive), Intel's and AMD's optimization manuals, and Arm's Software Optimization Guides
per core.

### 9.3 Memory

- **Cache line = 64 bytes** on essentially everything current. This is the fundamental
  unit; internalize it.
- **Sequential access is prefetched automatically; random access is not.** A linked list
  and an array with the same asymptotics differ by 10× in practice.
- **False sharing**: two threads writing different variables *in the same cache line*
  ping-pong the line between cores and destroy scaling. Pad to 64 (or 128 — some
  prefetchers work in pairs) bytes.
- **Structure of Arrays beats Array of Structures** for SIMD, almost always.
- **Non-temporal stores** (`movntdq`, `stnp`) bypass the cache for streaming writes you
  won't re-read. Powerful and easy to misuse.
- **Software prefetch** (`prefetcht0`, `prfm`) helps only when the hardware prefetcher
  can't see the pattern and you can issue it far enough ahead. **Usually it does nothing
  or hurts; measure.**

### 9.4 Branches

- Predictable branches ≈ free. Unpredictable ≈ 15–20 cycles.
- **Branchless with `cmov`/`csel`** trades a mispredict for a data dependency — a win when
  unpredictable, a loss when predictable (because it serializes what the predictor would
  have run ahead of).
- Loop alignment and target alignment sometimes matter; measure rather than cargo-cult.
- **⚠️ Do not use x86 branch-hint prefixes.** They've been ignored for two decades.

### 9.5 The rule

**[DURABLE] Measure, change one thing, measure again — on the actual target hardware.**
Assembly optimization without measurement is superstition, and the literature is full of
tricks that were true on a Pentium 4 and have been wrong ever since. Benchmark with real
data distributions, beware of the microbenchmark that keeps everything in L1, and be
suspicious of any speedup you can't explain mechanically.

---
