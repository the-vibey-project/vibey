---
id: skill-9-interpreters-and-jits-e5f546a950
purpose: 9 interpreters and jits
source: src/vibey_tools/skills/plugins/programming-language-development/skills/language-runtimes-interpreters-and-jits/SKILL.md
requires: ["skill-8-runtime-systems-4d2b38aeb9"]
links: []
---

## §9. Interpreters and JITs

### 9.1 The performance ladder

```
AST tree-walking       1×      Easiest to write. Correct. Slow. Start here.
Bytecode + switch      3–10×   The standard baseline.
Computed goto/threaded 1.5–2×  over switch. Better branch prediction. GCC/Clang extension.
Register bytecode      1.2–1.5× over stack bytecode. Fewer dispatches.
Inline caching         2–10×   on dynamic dispatch. The big win for dynamic languages.
Template/baseline JIT  2–5×    over interpreter. Fast to compile, no optimization.
Optimizing JIT         10–100× With type feedback + speculation + deopt.
AOT + PGO              comparable to JIT for static languages, no warmup
```

### 9.2 Interpreter techniques worth knowing

- **Direct threading / computed goto** — replace the dispatch `switch` with a jump table
  and a `goto *ip` at the end of each handler, giving the branch predictor one indirect
  branch per opcode instead of one shared branch. Typically 20–50%.
- **Superinstructions** — fuse common opcode pairs into one, cutting dispatch count.
- **Inline caching** — cache the result of a dynamic lookup at the call site.
  Monomorphic → polymorphic → megamorphic. **This plus hidden classes (§8.2) is why
  JavaScript is fast.**
- **NaN-boxing / pointer tagging** — avoid allocating for small values.
- **Register-based bytecode** — Lua's design; fewer instructions than a stack machine.

### 9.3 JIT

**Tiered execution** is the standard architecture: interpret first (fast start, gather
profile), then a baseline JIT for warm code, then an optimizing JIT for hot code, using
the profile to **speculate** — assume this call site is monomorphic, assume this integer
doesn't overflow, assume this type is stable — and **guard** each assumption, with
**deoptimization** back to the interpreter when a guard fails.

**[DURABLE] Deoptimization is the hardest part of a JIT.** You must be able to reconstruct
the exact interpreter state (locals, stack, PC) at any guard from optimized machine-code
state — which means every optimization must maintain that mapping. Get it wrong and you
get silent wrong answers, the worst possible failure mode.

**JIT-specific concerns**: W^X (memory must never be simultaneously writable and
executable), icache invalidation on ARM, on-stack replacement (OSR) for long-running loops,
code cache management, and the fact that a JIT is a **JIT-spraying attack surface**.

### 9.4 The bootstrapping and trust problem

If you write your compiler in your own language, you need an existing binary to build it —
and **Ken Thompson's "Reflections on Trusting Trust" (1984)** shows a compiler can be
backdoored such that the backdoor survives recompilation from clean source and is invisible
in the source. The practical answers: keep a documented bootstrap chain from a
minimal seed (Zig cites trivial bootstrapping as a *benefit* of dropping LLVM),
**reproducible builds**, and **diverse double-compiling** (David A. Wheeler's technique —
compile with two independent compilers and compare the outputs).
