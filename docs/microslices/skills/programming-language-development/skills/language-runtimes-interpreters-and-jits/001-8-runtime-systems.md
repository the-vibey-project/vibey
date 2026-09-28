---
id: skill-8-runtime-systems-4d2b38aeb9
purpose: 8 runtime systems
source: src/vibey_tools/skills/plugins/programming-language-development/skills/language-runtimes-interpreters-and-jits/SKILL.md
requires: []
links: ["skill-9-interpreters-and-jits-e5f546a950"]
---

## §8. Runtime Systems

### 8.1 Memory management

| Strategy | Cost | Used by |
|---|---|---|
| **Manual** | Zero runtime cost; UAF, leaks, double-free | C |
| **RAII + ownership** | Zero runtime cost; compile-time complexity | C++, Rust |
| **Reference counting** | Cheap latency, no pauses; **cycles leak**; refcount traffic is real, and atomic refcounts are expensive | Swift (ARC), CPython, Objective-C |
| **Tracing GC** | Handles cycles; throughput good; **pauses**; needs precise root/pointer identification | Java, Go, C#, JS, Haskell |
| **Arena/region** | Very fast alloc, bulk free; needs a lifetime discipline | Zig allocators, compilers themselves, request-scoped servers |

**Tracing GC design axes** [DURABLE]: **generational** (most objects die young — the
single most valuable GC insight ever), **moving vs. non-moving** (moving enables bump
allocation and compaction but requires precise pointer maps and read/write barriers),
**concurrent/incremental** (Go's low-latency collector; ZGC and Shenandoah's sub-millisecond
pauses), and **conservative vs. precise** (Boehm scans the stack conservatively — easy to
retrofit onto C, but can retain garbage and cannot move objects).

**[DURABLE] Your GC choice constrains your language design, not just your runtime.**
Precise GC requires the compiler to emit **stack maps** at every safepoint, which
constrains your calling convention, your optimizer (it must maintain the maps across
transformations), and your FFI (native code doesn't have maps — hence handles/pinning).
Deciding on GC late is not really possible.

### 8.2 The object model

Decisions here propagate everywhere: boxed vs. unboxed values (and whether small integers
are tagged — **NaN-boxing** is the standard trick in dynamic-language VMs, packing pointers
and integers into the unused bit patterns of IEEE-754 doubles), object headers (type,
GC mark bits, hash, lock word — every byte is multiplied by every object), field layout
(declared order or optimized packing; Rust reorders by default, C does not), method
dispatch (vtable, inline cache, hash lookup), and **hidden classes / shape trees**
(V8's mechanism for making dynamically-typed property access fast — arguably the single
biggest idea in modern dynamic-language performance).

### 8.3 Concurrency

| Model | Notes |
|---|---|
| OS threads + locks | Simple mapping; expensive; data races |
| **Green threads / goroutines** | M:N scheduling; **requires runtime support and growable stacks**; Go's segmented→copying stack evolution is instructive |
| **async/await** | No runtime threads needed; **function colouring** |
| Actors | Isolation by construction (Erlang, Akka) |
| CSP / channels | Go, Occam |
| Structured concurrency | Lifetimes of tasks bounded by scope. **The clear modern direction** — Kotlin, Swift, Java's virtual threads, Trio |
| Algebraic effects | OCaml 5 — concurrency without colouring (§4.9 → `language-design-parsing-and-types`) |

**[CONTESTED] Function colouring.** async/await splits your function universe in two:
async functions can only be awaited by async functions, so any library that becomes async
forces its callers to. *Against*: it fragments ecosystems (Python and Rust both have
visible sync/async library splits), and it's an ad-hoc effect system with none of the
polymorphism. *For*: it's explicit about where suspension happens, needs no runtime, works
in `no_std` and embedded contexts, and makes cost visible. Green threads/virtual threads
avoid colouring at the cost of requiring runtime support — which is precisely why Rust
removed green threads before 1.0 and Java added them in 2023.

### 8.4 Errors and unwinding

**Exceptions**: zero-cost when not thrown (table-driven unwinding; the tables live in
`.eh_frame`/`.gcc_except_table`), expensive when thrown. Requires unwinding-table
generation in the back end and destructor/cleanup landing pads — this is a *significant*
back-end feature, not a library concern.

**Result/Option types**: explicit, composable, no unwinder needed, but verbose without
sugar (`?` in Rust, `try` in Swift/Zig). **[DURABLE] The ergonomics live or die on the
propagation operator** — Go's pre-1.13 `if err != nil` verbosity is the standard cautionary
example.

**Panics/aborts** for unrecoverable errors. Decide early whether panics unwind or abort;
it affects the ABI, FFI safety (**unwinding across an FFI boundary into C is UB unless
both sides agreed**), and whether destructors run.

### 8.5 FFI

**[DURABLE] Your C FFI is the interface to forty years of existing software, and it will
be used more than you expect.** The hard parts: type mapping (especially strings — length
vs. NUL-terminated, and encoding), ownership across the boundary (who frees?), callbacks
into managed code (GC roots! stack maps!), thread attachment, error propagation, and
**never letting an exception or panic escape into C**.

Design decisions worth copying: Rust's `extern "C"` + `#[repr(C)]` (explicit ABI opt-in
per type and function), Zig's ability to `@cImport` C headers directly, and Swift's
generated header approach. **The single best decision is making the unsafe boundary
syntactically visible** so it's greppable and reviewable.

---
