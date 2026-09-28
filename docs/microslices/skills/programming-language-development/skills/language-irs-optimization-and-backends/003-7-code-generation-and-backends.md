---
id: skill-7-code-generation-and-backends-a03c48fa76
purpose: 7 code generation and backends
source: src/vibey_tools/skills/plugins/programming-language-development/skills/language-irs-optimization-and-backends/SKILL.md
requires: ["skill-6-optimization-dba4d38c9a"]
links: []
---

## §7. Code Generation and Backends

### 7.1 Choosing a backend

| Backend | Best for | Trade-offs |
|---|---|---|
| **LLVM** | Production compilers wanting best-in-class optimization and broad targets | **Excellent codegen; slow compilation; a very large C++ dependency; API churn across versions** |
| **Cranelift** | Fast compilation, JIT, WebAssembly, debug builds | Written in Rust; fast; **less optimization than LLVM**; used by Wasmtime and as rustc's alternative backend |
| **GCC (libgccjit / gccrs-style frontend)** | Targets LLVM doesn't support; GPL ecosystem | Fewer frontends use it; different integration model |
| **Custom** | Full control, no dependency, fast debug builds, unusual targets | You now own instruction selection, register allocation, and every target |
| **WebAssembly** | Portability, sandboxing, plugins | §7.5 |
| **Transpile to C** | Maximum portability, bootstrap | You inherit C's UB and lose debuggability |
| **Bytecode + interpreter** | Fastest path to a working language | Slow; see §9 → `language-runtimes-interpreters-and-jits` |

**[VERSIONED — a live and instructive case study.] The LLVM-dependency question is being
tested in public right now by two projects:**
- **Zig** is deliberately reducing its LLVM dependency. Its **self-hosted x86_64 backend
  became the default for Debug mode**, with dramatic reported compile-time wins (a hello
  world going from ~22.8 s to ~275 ms; the Zig compiler itself from ~75 s to ~20 s). By
  2026, Zig's own release notes state that **its x86 backend is more robust than its LLVM
  backend in terms of implementing the Zig language**, and a tracking issue exists to
  remove LLVM, LLD, and Clang libraries from the compiler entirely. The stated payoff:
  "all our bugs are belong to us," trivial bootstrapping, and in-place incremental binary
  patching. Zig 0.16 (April 2026) added architectures — Alpha, KVX, MicroBlaze, OpenRISC,
  PA-RISC, SuperH — while *removing* Solaris, AIX, and z/OS support.
- **rustc** keeps LLVM as the production backend but ships **Cranelift** as an alternative
  for debug builds. Measured on large real projects (Zed, Tauri, hickory-dns), it delivers
  roughly a **20% reduction in code generation time**, translating to about a **5% speedup
  in total clean-build time**. Note the ratio: **codegen is only ~25% of the wall clock**,
  which is the honest counterargument to "replace LLVM to get fast builds." rustc also
  maintains a GCC backend, and abstracts over all three via `rustc_codegen_ssa`.

**[DURABLE] The generalizable lesson: LLVM gives you world-class output slowly. If your
users' dominant pain is edit-compile-test latency rather than runtime performance, a
second, fast, dumb backend is a better investment than optimizing your LLVM usage** — and
architecting for *two* backends from the start (as rustc did with `rustc_codegen_ssa`) is
much cheaper than retrofitting.

### 7.2 Instruction selection

Map IR operations to target instructions. Approaches: **macro expansion** (one IR op → a
fixed instruction sequence; simple, poor code), **tree pattern matching with dynamic
programming** (Aho–Johnson / BURS / iburg; optimal per-tree), **DAG-based** (LLVM
SelectionDAG — handles shared subexpressions), and **GlobalISel** (LLVM's newer
IR-to-machine-IR framework, designed to be faster and more incremental than SelectionDAG).

### 7.3 Register allocation

**[DURABLE] Optimal register allocation is NP-complete** (it's graph colouring — Chaitin's
1981 reduction). The practical approaches:

| Algorithm | Notes |
|---|---|
| **Linear scan** | Fast, decent output. **The right choice for a JIT or a debug-build backend.** Poletto & Sarkar |
| **Graph colouring** (Chaitin–Briggs) | Better output, slower. Traditional AOT choice |
| **SSA-based** | Interference graphs of SSA programs are **chordal**, so colouring is polynomial. An elegant and increasingly common result worth knowing |
| **PBQP** | Partitioned boolean quadratic programming; handles irregular architectures |

The hard parts are always: **spilling** (choosing what to evict — usually by loop depth and
next-use distance), **coalescing** (removing redundant moves without making the graph
uncolourable), **live-range splitting**, and **calling-convention and register-class
constraints** (which are far more of the real work than the colouring algorithm).

### 7.4 The ABI

**[DURABLE] The ABI is the hardest under-appreciated part of a back end**, and getting it
wrong produces bugs that only appear when crossing a language boundary. You must specify:
calling convention (argument registers, stack layout, who cleans up), struct passing rules
(by value in registers? by hidden pointer? the System V x86-64 classification algorithm is
genuinely intricate), return values (including small aggregates), name mangling, stack
alignment (16 bytes on x86-64 SysV — violate it and SSE code faults), varargs, exception
unwinding tables, and TLS.

> **⚠️ GOTCHA — you cannot invent your own ABI and also interoperate.** If you want C FFI
> (you do — §8.5 → `language-runtimes-interpreters-and-jits`), you must implement the platform ABI exactly, including its ugly corners.
> Most new languages have at least one embarrassing "we passed a small struct wrong on
> Windows ARM64" bug.

### 7.5 WebAssembly as a target

**[VERSIONED — this changed materially in 2026.]** Wasm is a genuinely good compilation
target: a stack machine with structured control flow, a linear memory, and strong
sandboxing guarantees.

**WASI 0.3.0 was released on 11 June 2026**, and the change is architectural rather than
incremental: **native async is moved down into the Component Model's canonical ABI**, with
`async func`, `stream<T>`, and `future<T>` as primitives. The `wasi:io` package —
pollables, input-streams, output-streams — **is removed entirely**, absorbed into the
canonical ABI. The motivating problem is worth understanding because it's a general
lesson in interface design: under WASI 0.2, a `pollable` was a resource scoped to a single
component instance, so in a chain A→B→host, **component B could not forward the host's
wake-ups to A** and had to actively poll just to relay readiness. In 0.2 every component
needed its own event loop with no way to coordinate. Most 0.2→0.3 signature changes are
described as mechanical.

**What this means for a language implementer**: the **Component Model** plus **WIT**
(the interface definition language) plus the canonical ABI turns Wasm from "a module with
ad-hoc host glue" into a **typed, language-agnostic service boundary** — a component
declares what it needs and provides, and the host or linker wires the edges. Bindings
generators can now emit *idiomatic async* bindings per language. Wasmtime 45 ran the RC;
Wasmtime 46 ships 0.3.0. **A formally specified Component Model 1.0 is the next milestone**,
previewed at the Bytecode Alliance Plumbers Summit and Wasm I/O 2026.

**The honest caveats**, which the ecosystem states openly: **WASI still has no native
multi-threading**, which quietly rules out whole categories of compute-heavy server
workloads; **WASI 1.0 is planned but not shipped**; and adoption remains concentrated in
specific niches (edge functions, plugin systems) rather than general server compute —
Fermyon's edge platform and wasmCloud deployments are real, but they are chosen niches.
Note also that reporting on WASI versions is unusually inconsistent — you will find
sources in 2026 simultaneously describing 0.3 as "released," "in preview," and "the next
milestone." Check `wasi.dev` directly.
