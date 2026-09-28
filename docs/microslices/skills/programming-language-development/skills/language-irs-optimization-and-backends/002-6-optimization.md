---
id: skill-6-optimization-dba4d38c9a
purpose: 6 optimization
source: src/vibey_tools/skills/plugins/programming-language-development/skills/language-irs-optimization-and-backends/SKILL.md
requires: ["skill-5-intermediate-representations-cdb168f846"]
links: ["skill-7-code-generation-and-backends-a03c48fa76"]
---

## §6. Optimization

### 6.1 The passes, by category

| Category | Passes |
|---|---|
| **Local / peephole** | Constant folding, algebraic simplification, strength reduction, instruction combining |
| **Data-flow** | Constant propagation (SCCP), dead code elimination, common subexpression elimination, **GVN**, copy propagation |
| **Control-flow** | Branch folding, jump threading, block merging, tail duplication, **loop rotation** |
| **Loop** | LICM (loop-invariant code motion), unrolling, fusion/fission, interchange, strength reduction of induction variables, **vectorization** |
| **Interprocedural** | **Inlining** (the most important one), specialization, IPO/LTO, devirtualization, escape analysis |
| **Memory** | **SROA/mem2reg** (scalar replacement of aggregates — promoting memory to SSA registers), alias analysis, load/store forwarding |
| **Layout** | Basic-block placement, PGO-driven hot/cold splitting |

**[DURABLE] The 80/20 of optimization is inlining plus mem2reg/SROA plus constant folding
plus DCE.** Inlining exposes opportunities for everything else — it's a *meta*-optimization.
mem2reg turns naive stack-slot-per-variable codegen into real SSA, which is why a front end
can emit dumb, obviously-correct code and still get fast output.

### 6.2 The rules

1. **Correctness always beats speed.** A miscompile costs more than any optimization saves,
   and it destroys trust in the whole toolchain. Compiler bugs are the bugs users trust
   least and debug worst.
2. **Measure.** Optimizations interact non-obviously; your intuition about which passes
   matter will be wrong. Build the benchmark suite before the pass.
3. **Pass ordering matters and has no optimal solution** — the "phase-ordering problem."
   LLVM's pipeline is a hand-tuned sequence with several passes run more than once. Accept
   this; don't look for elegance here.
4. **Undefined behaviour is an optimization contract, and it is dangerous.** UB lets the
   optimizer assume things (no signed overflow, no null dereference, no strict-aliasing
   violation) and is the source of the most surprising and hostile compiler behaviour in C
   and C++. **If you're designing a new language, define the behaviour** — even "wraps" or
   "traps" or "unspecified but not undefined" is enormously better. Rust's decision to make
   overflow panic in debug and wrap in release is a defensible model.
5. **Debug builds must be fast to produce and debuggable.** `-O0` should be a genuinely
   different, minimal pipeline, not the same pipeline with fewer passes.

### 6.3 Where optimization happens

Modern systems do it at several levels, and it matters which:
- **Front end / high IR**: language-specific optimizations you can't express later
  (devirtualizing based on trait resolution, eliminating bounds checks using type
  information, monomorphization).
- **Mid-level (LLVM IR)**: the general-purpose bulk.
- **Link time (LTO/ThinLTO)**: cross-module inlining and devirtualization. **ThinLTO** is
  the scalable variant, using summaries rather than merging everything into one module.
- **Runtime (JIT)**: speculative optimization using real profile data (§9.3 → `language-runtimes-interpreters-and-jits`).
- **PGO/BOLT**: profile-guided layout, applied to already-linked binaries.

---
