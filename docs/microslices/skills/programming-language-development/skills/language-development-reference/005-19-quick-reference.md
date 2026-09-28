---
id: skill-19-quick-reference-5c320698b3
purpose: 19 quick reference
source: src/vibey_tools/skills/plugins/programming-language-development/skills/language-development-reference/SKILL.md
requires: ["skill-18-the-canon-3e50e94c77"]
links: ["skill-20-sources-and-method-b57af3a6c1"]
---

## §19. Quick Reference

### 19.1 If you're building one, in order
1. **Read *Crafting Interpreters*.** Build a tree-walking interpreter. Ship it.
2. **Design the CST and spans before anything else** (§2.4 → `language-design-parsing-and-types`, §10.4 → `language-diagnostics-tooling-and-evolution`).
3. Hand-written recursive descent + Pratt, **with error recovery** (§2.2 → `language-design-parsing-and-types`–2.3).
4. Name resolution as a separate, queryable phase (§3.1 → `language-design-parsing-and-types`, §11.2 → `language-diagnostics-tooling-and-evolution`).
5. Type checker — **bidirectional** unless you have a reason (§4.2 → `language-design-parsing-and-types`).
6. **Exhaustiveness checking** — highest value per line of code you will write (§4.7 → `language-design-parsing-and-types`).
7. Bytecode VM, so you have a working language.
8. **A typed, verifiable, printable mid-level SSA IR** (§5 → `language-irs-optimization-and-backends`).
9. mem2reg/SROA + inlining + constant folding + DCE. Stop. Measure (§6.1 → `language-irs-optimization-and-backends`).
10. Backend: **LLVM for output quality, Cranelift/custom for speed** — and abstract over
    the choice from the start (§7.1 → `language-irs-optimization-and-backends`).
11. Diagnostics, snapshot-tested (§10 → `language-diagnostics-tooling-and-evolution`).
12. Language server, from the same engine (§11 → `language-diagnostics-tooling-and-evolution`).
13. Formatter, package manager, docs, debugger (§13 → `language-diagnostics-tooling-and-evolution`).

### 19.2 Numbers worth knowing
- Optimal register allocation is **NP-complete**; SSA interference graphs are **chordal**,
  so SSA-form allocation is polynomial.
- Interpreter ladder: bytecode ~**3–10×** over tree-walking; computed goto ~**1.5–2×** over
  switch; optimizing JIT **10–100×** over interpreter (§9.1 → `language-runtimes-interpreters-and-jits`).
- Cranelift in rustc: ~**20%** codegen-time reduction → ~**5%** total clean build.
- Zig self-hosted x86 backend: hello world **22.8 s → 275 ms**; self-build **75 s → 20 s**.
- Csmith found **hundreds** of bugs in GCC and LLVM and **zero** in CompCert's verified
  middle end.
- LLVM ships roughly **every 6 months**; GCC roughly **annually** (16.1: April 2026).

### 19.3 Compiler-bug triage
| Symptom | Look at |
|---|---|
| Wrong answer at `-O2`, right at `-O0` | **Miscompile.** Bisect passes (`opt-bisect-limit`), check UB in the source first |
| Compiler hangs | Occurs check, trait/instance resolution loop, unbounded comptime, pathological backtracking |
| Stack overflow in the compiler | Deep recursion on nested expressions — most compilers need an explicit depth limit or a manual stack |
| Wrong across an FFI boundary | ABI: struct classification, alignment, varargs, unwinding (§7.4 → `language-irs-optimization-and-backends`) |
| Works in debug, fails in release | UB, uninitialized memory, or an unsound optimization |
| Error message points at the wrong place | Span lost during lowering or desugaring (§10.4 → `language-diagnostics-tooling-and-evolution`) |
| IDE and compiler disagree | Two implementations, or a stale query cache (§11 → `language-diagnostics-tooling-and-evolution`) |

---
