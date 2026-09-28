---
id: skill-17-currency-snapshot-verified-august-2026-195d089bbe
purpose: 17 currency snapshot verified august 2026
source: src/vibey_tools/skills/plugins/programming-language-development/skills/language-development-reference/SKILL.md
requires: ["skill-16-contested-questions-09580a9a30"]
links: ["skill-18-the-canon-3e50e94c77"]
---

## §17. Currency Snapshot — verified August 2026

| Thing | Status as of Aug 2026 | Decay risk |
|---|---|---|
| **LLVM** | **22.1.x** current (22.1.0 released 24 Feb 2026; 22.1.8 in June). ~6-month feature cadence. LLVM 22 adds Armv9.7-A and GICv5 assembly support, C2y work in Clang (named loops), full MLIR-to-LLVM-IR translation for OpenMP TASKLOOP, RISC-V tail folding by default, ThinLTO distributed-build improvements | Medium |
| **MLIR** | Ships in the LLVM monorepo, moves with its releases; no separate qualification of the release branch. Substrate for Mojo, IREE, Triton, Flang | Medium |
| **GCC** | **16.1** released 30 April 2026. **C++20 by default**; ships **C++26 reflection and contracts** and safety hardening. ⚠️ **C++20 modules still experimental, requiring `-fmodules`** | Medium |
| **C++26** | ⚠️ **Done.** WG21 completed technical work **28 March 2026** (London Croydon; 210 experts, 24 nations); officially shipped by WG21 that date. Headline: **static reflection, contracts, `std::execution`, hardened stdlib**. Reflection operator changed `^` → `^^` during standardization. **`[[profiles::enforce]]` deferred to C++29**; Safe C++ borrow-checking proposal rejected. Herb Sutter stepped down as convener | Low |
| **WASI** | ⚠️ **WASI 0.3.0 released 11 June 2026.** Native async moved into the Component Model canonical ABI (`async func`, `stream<T>`, `future<T>`); **`wasi:io` removed entirely**. Wasmtime 45 ran the RC, Wasmtime 46 ships it; jco supports it. 0.2 remains supported/virtualizable. **Component Model 1.0 (formally specified) is the next milestone**; **WASI 1.0 planned, not shipped**. ⚠️ **Still no native multithreading.** Reporting on version status is inconsistent — check wasi.dev | **High** |
| **Zig** | **0.16 (beta) April 2026**; 0.17 in progress. Self-hosted **x86_64 backend default in Debug**; reported hello-world compile 22.8 s → 275 ms, self-build 75 s → 20 s. Release notes state the **x86 backend is now more robust than the LLVM backend** for implementing Zig. Open tracking issue to remove LLVM/LLD/Clang libraries entirely. 0.16 added Alpha/KVX/MicroBlaze/OpenRISC/PA-RISC/SuperH; **removed Solaris, AIX, z/OS** | **High** |
| **rustc backends** | LLVM production; **Cranelift** available via `rustup component add rustc-codegen-cranelift-preview` and `[profile.dev] codegen-backend = "cranelift"`. Measured ~**20% codegen-time reduction → ~5% total clean-build speedup** on Zed/Tauri/hickory-dns. GCC backend also maintained; all three behind `rustc_codegen_ssa` | Medium |
| **rustc type system** | **Next-gen trait solver** and **Polonius alpha**: both targeted for stabilization, with CI testing being expanded (compiler-team MCP, June 2026). Polonius worst case measured at ~60% slower than NLL on a pathological 5 KLOC function (42K loans, 255K statements, 125K outlives constraints) | **High** |
| **Cranelift** | 0.127.x (Dec 2025). Supports x86-64, aarch64, s390x, riscv64. Production use in Wasmtime | Medium |
| **gccrs** | ⚠️ **Still experimental.** Stated **2026 goal: be able to *mis*-compile the Linux kernel.** Handles simple standalone programs as of mid-2026; spent H1 2026 fixing attribute handling, name resolution, and resource management against kernel crates. Milestones: embedded → Rust-for-Linux → general purpose. Targets **Rust 1.49** semantics, not current Rust | Medium |
| **Mojo** | **1.0.0 beta1, 7 May 2026.** Chris Lattner / Modular; MLIR-based; Linux and macOS. **Language under the Modular Community License** (stdlib Apache-2.0-with-LLVM-exceptions) — *not* fully open source | **High** |
| **Carbon** | Experimental. Experimental **MVP 0.1 expected late 2026 at the earliest; production 1.0 after 2028** | Medium |

**Goes stale fastest:** WASI/Component Model versions; Zig's backend and LLVM-removal
progress; rustc's Polonius/next-solver status; Mojo. **Essentially never stale:** §1 → `language-design-parsing-and-types`
(design principles), §2 → `language-design-parsing-and-types` (parsing), §4.2 → `language-design-parsing-and-types`–4.3 (inference and unification), §5.2 → `language-irs-optimization-and-backends` (SSA),
§6.1 → `language-irs-optimization-and-backends` (the passes), §7.3 → `language-irs-optimization-and-backends` (register allocation), §9 → `language-runtimes-interpreters-and-jits` (interpreter ladder), §10 → `language-diagnostics-tooling-and-evolution` (diagnostics),
§15 (anti-patterns).

---
