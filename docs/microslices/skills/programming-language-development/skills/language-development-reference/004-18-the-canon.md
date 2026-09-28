---
id: skill-18-the-canon-3e50e94c77
purpose: 18 the canon
source: src/vibey_tools/skills/plugins/programming-language-development/skills/language-development-reference/SKILL.md
requires: ["skill-17-currency-snapshot-verified-august-2026-195d089bbe"]
links: ["skill-19-quick-reference-5c320698b3"]
---

## §18. The Canon

### 18.1 Books

| Author | Work | Why |
|---|---|---|
| **Robert Nystrom** | ***Crafting Interpreters*** | **Free online.** The best starting point in existence: a tree-walker and a bytecode VM, both complete, both explained. Start here, always |
| Aho, Lam, Sethi, Ullman | *Compilers: Principles, Techniques, and Tools* ("the Dragon Book") | The classic. Strong on parsing theory, dated on modern back ends |
| **Appel** | ***Modern Compiler Implementation in ML/Java/C***; ***Compiling with Continuations*** | The best structured treatment of a full compiler; CwC is the CPS reference |
| **Muchnick** | *Advanced Compiler Design and Implementation* | The optimization reference. Dense, comprehensive, still the standard |
| **Cooper & Torczon** | *Engineering a Compiler* | The best modern textbook; better back-end coverage than the Dragon Book |
| **Pierce** | ***Types and Programming Languages*** (TAPL) | **The** type systems book. If you're designing a type system, this is not optional |
| Pierce (ed.) | *Advanced Topics in Types and Programming Languages* | The sequel: dependent types, subtyping, effects |
| **Harper** | *Practical Foundations for Programming Languages* | Rigorous, opinionated, structural |
| **Krishnamurthi** | *Programming Languages: Application and Interpretation* | **Free.** Excellent on design trade-offs |
| **Friedman & Wand** | *Essentials of Programming Languages* | Interpreters as the lens for understanding semantics |
| **Jones, Hosking, Moss** | ***The Garbage Collection Handbook*** | The GC reference, full stop |
| Smith & Nair | *Virtual Machines* | VM and JIT architecture |
| **Wirth** | *Compiler Construction* | Short, clear, complete. A single-sitting read |
| Grune et al. | *Parsing Techniques* | Exhaustive on parsing |

### 18.2 Papers worth reading directly

- **Cytron et al. (1991)**, "Efficiently Computing Static Single Assignment Form" — the
  classic SSA construction.
- **Braun et al. (2013)**, "Simple and Efficient Construction of SSA Form" — **use this one**.
- **Appel (1998)**, "SSA is Functional Programming" — the unifying insight.
- **Maranget (2007)**, "Warnings for Pattern Matching" — exhaustiveness checking.
- **Dunfield & Krishnaswami**, "Bidirectional Typing" (survey) — the modern inference guide.
- **Damas & Milner (1982)** — Algorithm W.
- **Chaitin (1981)** — register allocation as graph colouring; **Poletto & Sarkar (1999)** —
  linear scan; **Hack et al.** — SSA-based allocation and chordality.
- **Yang, Chen, Eide, Regehr (2011)**, "Finding and Understanding Bugs in C Compilers" —
  the Csmith paper, and the empirical case for verification.
- **Leroy**, the CompCert papers.
- **Thompson (1984)**, "Reflections on Trusting Trust."
- **Gabriel (1989)**, "Worse is Better."
- **Plotkin & Pretnar**, algebraic effects and handlers; **Leijen** on Koka.
- **Grossman et al.**, Cyclone (regions) — the direct ancestor of Rust's ownership model.

### 18.3 Primary sources and ongoing

- **LLVM**: `llvm.org/docs` (the Language Reference and Kaleidoscope tutorial), the
  discourse forums, `mlir.llvm.org`. **`rustc-dev-guide.rust-lang.org`** is arguably the
  best publicly-written description of a production compiler's architecture.
- **Cranelift** (`cranelift.dev`), **Wasmtime**, **Bytecode Alliance** blog,
  **`wasi.dev`**, the **Component Model book**.
- **Language design in public**: Rust RFCs and Inside Rust blog, Rust project goals,
  **Python PEPs**, **WG21 papers** (`open-std.org/jtc1/sc22/wg21`) and Herb Sutter's trip
  reports, Swift Evolution, Go proposals and the `research.swtch.com` design essays.
- **Zig devlog** (`ziglang.org/devlog`) — an unusually candid running account of compiler
  engineering decisions.
- **Conferences**: PLDI, POPL, OOPSLA, ICFP, CGO, SPLASH; the LLVM Developers' Meeting;
  Strange Loop's archive.
- **People to read**: Chris Lattner (LLVM, Swift, MLIR, Mojo), Graydon Hoare (Rust; his
  retrospective essays on language design are excellent), Andrew Kelley (Zig), Rich Hickey
  (design talks), Simon Peyton Jones (GHC, and the clearest explainer in the field),
  Niko Matsakis (Rust types), Russ Cox (Go), Anders Hejlsberg (Turbo Pascal, C#,
  TypeScript), Jonathan Corbet's LWN coverage of toolchain work.

---
