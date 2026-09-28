---
id: skill-5-intermediate-representations-cdb168f846
purpose: 5 intermediate representations
source: src/vibey_tools/skills/plugins/programming-language-development/skills/language-irs-optimization-and-backends/SKILL.md
requires: []
links: ["skill-6-optimization-dba4d38c9a"]
---

## §5. Intermediate Representations

### 5.1 Why more than one

**[DURABLE] Every serious compiler has at least three IR levels**, because the
transformations you want at each level need different information:
```
AST            source-shaped. Names, sugar, full spans. For type checking & diagnostics.
  ↓ desugar, resolve
HIGH IR        typed, desugared, still source-ish. For borrow checking, exhaustiveness,
               source-level optimizations.        (rustc: HIR → THIR)
  ↓ lower
MID IR         explicit control flow (CFG), explicit memory ops, SSA. THE optimization IR.
                                                 (rustc: MIR · Swift: SIL · Go: SSA · LLVM IR)
  ↓ lower
LOW IR         machine-shaped, target types, still virtual registers.  (LLVM MachineIR)
  ↓
MACHINE CODE
```
The rule of thumb: **lower when the information you're about to discard is no longer
needed, and no sooner.** Lowering too early loses the ability to give good errors and to
do high-level optimizations; lowering too late means every pass has to handle sugar.

### 5.2 SSA — Static Single Assignment

**[DURABLE] SSA is the dominant mid-level IR form and has been since the early 1990s.**
Every variable is assigned exactly once; control-flow merges use **φ (phi) functions**.

```
                      entry:
x = 1                   x₁ = 1
if c: x = 2             br c, then, join
y = x + 1             then:
                        x₂ = 2
                        br join
                      join:
                        x₃ = φ(x₁ from entry, x₂ from then)
                        y₁ = x₃ + 1
```
**Why it matters**: def-use chains are explicit and immediate, so constant propagation,
dead code elimination, GVN, and register allocation all become dramatically simpler. You
no longer need separate reaching-definitions analysis — SSA *is* that analysis, cached in
the IR.

**Construction**: the classic algorithm is Cytron et al. (1991) using **dominance
frontiers** to place φ-nodes. The modern practical alternative is **Braun et al. (2013),
"Simple and Efficient Construction of Static Single Assignment Form"** — builds SSA
directly during AST-to-IR translation without a separate dominance computation. **If you're
writing a compiler today, use Braun**; it is far simpler and produces comparable results.

**Destruction**: φ-nodes aren't real instructions. Converting out of SSA means inserting
copies on incoming edges, and doing it naively causes the **lost-copy** and **swap**
problems. Sreedhar et al.'s method is the standard correct approach. **This is where
subtle miscompiles live.**

### 5.3 The other IR forms

- **CPS (continuation-passing style)** — every call is a tail call; control flow is
  explicit as data. Elegant for functional languages, first-class control (call/cc), and
  compiler correctness proofs. Used by SML/NJ; the classic reference is Appel's
  *Compiling with Continuations*.
- **ANF (A-normal form)** — all intermediate results named, arguments are atomic. Roughly
  "CPS's benefits without the plumbing," and easier to read. Common in functional compilers.
- **Sea of nodes** — a graph where control and data dependencies are unified, allowing
  aggressive reordering. **HotSpot C2** and **V8's TurboFan** use it. Powerful, and
  notoriously hard to debug — V8 has been moving *away* from it in parts of the pipeline,
  which is worth knowing before you adopt it.
- **Stack-based bytecode** — JVM, CPython, WebAssembly. Compact, trivial to generate,
  slower to interpret than register-based.
- **Register-based bytecode** — Lua, Dalvik, LuaJIT. Fewer instructions dispatched;
  measurably faster interpretation.

**[DURABLE] CPS/ANF/SSA are the same thing viewed differently.** Appel's "SSA is Functional
Programming" (1998) is the paper that makes this click: an SSA φ-node is a function
parameter of a basic block, and a basic block is a continuation.

### 5.4 MLIR — multi-level IR as infrastructure

**[VERSIONED]** MLIR generalizes "have several IRs" into a framework: instead of one fixed
IR, you define **dialects** — extensible sets of operations, types, and attributes — and
write **progressive lowering** passes between them. A single module can hold operations
from several dialects at once.

Why it matters: it's the substrate for the ML-compiler ecosystem (TensorFlow, IREE, Triton),
for **Mojo** (Chris Lattner's language, explicitly built on MLIR), for Flang's OpenMP
lowering, and increasingly for hardware-adjacent domains. It ships inside the LLVM
monorepo, so it moves with LLVM's release train.

**When MLIR is right**: you have multiple abstraction levels, domain-specific optimizations,
heterogeneous targets (CPU/GPU/accelerator), or you want to reuse a large pass and
infrastructure ecosystem. **When it isn't**: a straightforward language targeting CPUs —
MLIR's conceptual overhead and build weight are substantial, and plain LLVM IR is a much
shorter path.

### 5.5 Practical IR design rules

1. **Make it verifiable and write the verifier first.** Run it after every pass in debug
   builds. This catches more miscompiles than any other single practice.
2. **Make it printable and parseable.** A textual round-trippable form makes every bug
   report, every test, and every debugging session tractable. LLVM's `.ll` format is the
   reason LLVM is debuggable at all.
3. **Explicit is better than implicit.** Make types, effects, and control flow explicit in
   the IR even when it's verbose.
4. **Preserve source locations through every transformation** or debug info and diagnostics
   degrade silently (§10.4 → `language-diagnostics-tooling-and-evolution`).
5. **Design for testability**: passes should be individually runnable on IR files.

---
