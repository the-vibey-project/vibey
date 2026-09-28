---
id: skill-11-incremental-compilation-and-ide-support-617ae6487f
purpose: 11 incremental compilation and ide support
source: src/vibey_tools/skills/plugins/programming-language-development/skills/language-diagnostics-tooling-and-evolution/SKILL.md
requires: ["skill-10-diagnostics-2bcb23ad28"]
links: ["skill-12-testing-and-verification-e923e8e202"]
---

## §11. Incremental Compilation and IDE Support

### 11.1 The requirement has changed

**[DURABLE] A modern language needs a language server, and a batch compiler cannot become
one by accident.** The IDE's requirements are qualitatively different from the batch
compiler's:

| Batch compiler | Language server |
|---|---|
| Complete, valid input | **Always-broken input** |
| Whole program | One file changed, answer in <100 ms |
| Throughput | **Latency** |
| Correct errors | Best-effort answers, always |
| Can exit | Long-running, memory-bounded |

Two architectural answers: **one engine serving both** (rust-analyzer converging with
rustc; Roslyn; the TypeScript compiler) or **two implementations** (which guarantees
divergent behaviour and double the bug surface). The first is right and expensive.

### 11.2 The techniques

- **Query-based / demand-driven architecture.** Instead of running phases in order, express
  everything as memoized queries (`type_of(def)`, `resolve(name)`) over a dependency graph;
  on change, invalidate transitively and recompute only what's needed. This is rustc's
  query system and rust-analyzer's **salsa**, and it is the dominant design.
- **Red-green / persistent trees** (§2.4 → `language-design-parsing-and-types`) for cheap structural sharing across edits.
- **Firewalls**: hash intermediate results so that a change that doesn't alter a result
  stops propagating (reformatting a function body shouldn't invalidate its callers).
- **Laziness**: don't type-check function bodies you weren't asked about.
- **Interning** everything (strings, types, spans) so comparison is pointer equality.

**[DURABLE] Design your compiler as a query system from the beginning.** Retrofitting
incrementality onto a phase-ordered compiler is one of the largest refactors a compiler
team can undertake, and several major projects have spent years on it.

### 11.3 What the LSP needs from you

Completion (on broken input, ranked), go-to-definition, find-references (needs a
reverse index), hover types, rename (needs to know *every* reference, including in
macros and strings-that-are-code), diagnostics on the fly, signature help, semantic
highlighting, code actions, formatting, and inlay hints. **Each one is a query your
compiler must be able to answer about a partial program.**

---
