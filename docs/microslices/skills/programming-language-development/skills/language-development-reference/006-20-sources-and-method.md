---
id: skill-20-sources-and-method-b57af3a6c1
purpose: 20 sources and method
source: src/vibey_tools/skills/plugins/programming-language-development/skills/language-development-reference/SKILL.md
requires: ["skill-19-quick-reference-5c320698b3"]
links: []
---

## §20. Sources and Method

**Method.** Narrative (not systematic) review. The durable material — §1 → `language-design-parsing-and-types` (design
principles), §2 → `language-design-parsing-and-types` (parsing), §4.2 → `language-design-parsing-and-types`–4.7 (type systems), §5.2 → `language-irs-optimization-and-backends` (SSA), §6 → `language-irs-optimization-and-backends` (optimization), §7.2 → `language-irs-optimization-and-backends`–7.4
(codegen), §8 → `language-runtimes-interpreters-and-jits` (runtimes), §9 → `language-runtimes-interpreters-and-jits` (interpreters and JITs), §10 → `language-diagnostics-tooling-and-evolution` (diagnostics), §12 → `language-diagnostics-tooling-and-evolution` (testing),
§15 (anti-patterns) — is synthesized from the primary literature and canonical texts in
§18. Every **time-sensitive** claim (toolchain versions, standard status, project state)
was verified against a primary or near-primary source in **August 2026** and is flagged in
§17 with a decay-risk rating. Where language designers genuinely disagree, §16 presents
both cases rather than adjudicating.

**Search log** (August 2026): LLVM current version and MLIR status · WebAssembly, WASI
Preview 3, and the Component Model · Zig's self-hosted backend and LLVM removal; Mojo and
Carbon status · rustc's Cranelift backend, Polonius, and the next-gen trait solver · C++26
finalization, contracts, reflection, and profiles · GCC 16 and gccrs.

**Primary and near-primary sources consulted (selected):**
- **LLVM Discussion Forums** release announcements (22.1.0 through 22.1.8); Arm's
  "What is new in LLVM 21/22" engineering blogs; **Phoronix** LLVM/Clang 22.1 coverage;
  `mlir.llvm.org` release notes
- **wasi.dev** — the WASI 0.3 release page and roadmap; **Bytecode Alliance** — "WASI 0.3
  Launched" and "The Road to Component Model 1.0"; the Component Model book
- **ziglang.org** — 0.16.0 release notes and the 2026 devlog; the ziglang/zig issue
  tracking LLVM/LLD/Clang removal; Ziggit and Lobsters discussion of the self-hosted x86
  backend default
- **Rust**: `rustc-dev-guide.rust-lang.org` (codegen backends, next-gen trait solving);
  the Rust Blog "Project goals update — April 2026"; rust-lang/compiler-team MCP #996 on
  CI-testing the next solver and Polonius alpha; the `rustc_codegen_cranelift` repo and
  the "Production-ready cranelift backend" project goal; **cranelift.dev**
- **Herb Sutter** — "C++26 is done! Trip report: March 2026 ISO C++ standards meeting";
  **InfoQ** and **isocpp.org** coverage of C++26 and GCC 16.1
- **gccrs** — the project's monthly reports (Dec 2025, Feb/Mar/May 2026), `rust-gcc.github.io`,
  **LWN.net** ("Progress toward compiling Linux with gccrs," "Gccrs after libcore")
- Canonical papers and books as listed in §18

**Confidence statement.** **High confidence** in §1–§13 → `language-design-parsing-and-types`, `language-diagnostics-tooling-and-evolution` and §15, §18–§19 — these rest on
the primary literature, canonical texts, and published compiler documentation. **High
confidence** in §17's verified items as of the stated date. **Moderate confidence** in the
performance figures quoted in §7.1 → `language-irs-optimization-and-backends` and §19.2: the Zig compile-time numbers come from
project announcements and community benchmarking rather than independent measurement, and
the Cranelift figures come from the Rust project's own measurements on three named
projects — both are directionally reliable and should not be treated as general
multipliers. The **WASI status in §7.5 → `language-irs-optimization-and-backends` is the least stable content in this document**: it
changed during 2026, and contemporaneous secondary sources describe 0.3 inconsistently as
released, in preview, and forthcoming — the dates given here follow wasi.dev and the
Bytecode Alliance directly, and should be re-checked rather than quoted from memory.
