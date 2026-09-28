---
id: skill-12-testing-and-verification-e923e8e202
purpose: 12 testing and verification
source: src/vibey_tools/skills/plugins/programming-language-development/skills/language-diagnostics-tooling-and-evolution/SKILL.md
requires: ["skill-11-incremental-compilation-and-ide-support-617ae6487f"]
links: ["skill-13-standard-library-and-ecosystem-7936c14b56"]
---

## §12. Testing and Verification

### 12.1 The test pyramid for a compiler

- **Unit tests** per pass.
- **Snapshot/golden tests**: source in, expected output (IR, diagnostics, or machine code)
  out. Cheap, high-coverage, and the standard for diagnostics.
- **Execution tests**: compile and run, check behaviour. The real correctness signal.
- **Differential testing**: compare against another implementation or another optimization
  level. `-O0` vs `-O2` disagreement is a miscompile, full stop.
- **Metamorphic testing**: semantically equivalent programs must behave identically.
- **Fuzzing**: **Csmith** (random valid C generation) and **YARPGen** found hundreds of
  bugs in GCC and LLVM. **Alive2** does translation validation for LLVM peepholes — proving
  optimizations correct with an SMT solver. **If you have an optimizer, you need a fuzzer.**
- **Bootstrap tests**: compile the compiler with itself, compare stage2 and stage3 output.
  Byte-identical output is a strong signal.
- **Test suite reuse**: a new implementation of an existing language should run the
  existing conformance suite.

### 12.2 Formal verification

- **CompCert** — a formally verified C compiler in Coq. **The Yang et al. Csmith study
  found zero miscompiles in CompCert's verified middle end while finding hundreds in GCC
  and LLVM.** This is the strongest empirical evidence in the field for verification.
- **CakeML** — a verified ML compiler with a verified bootstrap.
- **Translation validation** — verify each *compilation run* rather than the compiler
  (Alive2). Far cheaper than full verification and applicable to existing compilers.
- **Mechanized semantics**: K framework, Redex, Lean/Coq formalizations. Even partially
  formalizing your semantics finds design bugs.

**[DURABLE] Full verification is expensive and mostly reserved for safety-critical
domains. Translation validation and fuzzing give most of the assurance for a fraction of
the cost** and should be in any serious compiler's CI.

---
