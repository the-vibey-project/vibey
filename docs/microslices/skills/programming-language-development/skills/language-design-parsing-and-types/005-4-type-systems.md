---
id: skill-4-type-systems-36543252d2
purpose: 4 type systems
source: src/vibey_tools/skills/plugins/programming-language-development/skills/language-design-parsing-and-types/SKILL.md
requires: ["skill-3-names-scopes-and-modules-4c018a1049"]
links: []
---

## §4. Type Systems

### 4.1 The design space

| Axis | Options |
|---|---|
| Checked when | Static, dynamic, gradual, optional |
| Inference | None, local, bidirectional, global (HM) |
| Polymorphism | Parametric (generics), ad-hoc (overloading/traits), subtype, row |
| Subtyping | None, nominal, structural, both |
| Variance | Invariant, co/contravariant, declaration-site or use-site |
| Higher-kinded | No, yes (Haskell, Scala) |
| Dependent | No, limited (const generics, refinement), full (Idris, Lean, Agda) |
| Effects | Implicit, checked exceptions, monadic, algebraic effect handlers |
| Linearity | None, affine (Rust ownership), linear, uniqueness |

### 4.2 Inference

**Hindley–Milner (Algorithm W)** — full inference for the let-polymorphic lambda calculus.
Unification-based, principal types, and no annotations required anywhere. The catch:
**HM does not survive contact with subtyping, higher-rank types, or type classes without
significant extension**, and its error messages are notoriously bad — unification fails at
some arbitrary point far from the actual mistake.

**Bidirectional type checking** — the modern default. Split into two mutually recursive
judgments: *checking* (`Γ ⊢ e ⇐ T`, "does `e` have type `T`?") and *synthesis*
(`Γ ⊢ e ⇒ T`, "what type does `e` have?"). Annotations at the boundaries.
- **Why it won**: it scales to subtyping, higher-rank polymorphism, dependent types, and
  GADTs, where HM does not; it needs fewer annotations than you'd think; and — the reason
  practitioners care — **error messages are dramatically better**, because when checking
  fails you know the *expected* type and can report both sides.
- Used in some form by Rust, Swift, TypeScript, Scala 3, Agda, Idris.

**Local type inference** (C#, Java, Go, C++ `auto`) — infer variable types from
initializers and generic instantiations from arguments; require annotations on function
signatures. **[DURABLE] Requiring signature annotations is a feature, not a limitation**:
it makes the code self-documenting, keeps errors local, makes separate compilation
tractable, and makes the IDE's job possible.

> **⚠️ GOTCHA — global inference and error locality are in direct tension.** With full
> inference, an error in one function can surface as a type error in an unrelated one.
> Every language with global inference eventually adds a "please annotate your top-level
> definitions" lint. Consider just requiring them.

### 4.3 Unification and the occurs check

```
unify(a, b):
  a, b = resolve(a), resolve(b)          # follow substitutions (union-find)
  match (a, b):
    (Var x, Var y) if x == y  -> ok
    (Var x, t) | (t, Var x)   -> occurs_check(x, t); bind(x, t)   ← DON'T SKIP THIS
    (Con(c1, as), Con(c2, bs)) if c1 == c2 && len equal -> zip-unify
    _                          -> type error (report BOTH sides and the location)
```
**The occurs check** prevents binding `x := List<x>`, which creates an infinite type. Skip
it and your compiler hangs or stack-overflows on a program like `let f = fun x -> x x`.
Use **union-find with path compression** for the substitution or unification is
accidentally quadratic.

**Levels/ranks for generalization**: the naive "generalize all free variables not in the
environment" is O(n) in environment size at every `let`. The standard fix is Rémy's
level-based generalization — tag each type variable with the `let`-depth at which it was
created and generalize only those deeper than the current level. Every efficient HM
implementation does this.

### 4.4 Traits, type classes, and interfaces

The mechanism for ad-hoc polymorphism, and it comes in three flavours:
- **Nominal interfaces** (Java, C#): a type explicitly declares it implements an interface.
  Simple, but you cannot retrofit an interface onto a type you don't own.
- **Structural** (Go, TypeScript): if it has the methods, it satisfies the interface. Fixes
  retrofitting; loses the ability to distinguish two interfaces with the same shape and
  different meaning.
- **Type classes / traits** (Haskell, Rust, Swift): implementations are declared
  *separately* from both the type and the interface. Solves retrofitting *and* keeps
  nominality — at the cost of needing **coherence** rules.

**Coherence and the orphan rule.** If two crates can both implement `Trait` for `Type`,
which one applies? Incoherence breaks type-directed dispatch and can break soundness.
Haskell and Rust enforce coherence via the **orphan rule**: you may implement a trait for
a type only if you own the trait or the type. It is the single most-complained-about rule
in Rust and it is load-bearing.

**Implementation strategies**: dictionary passing (pass a vtable of the implementation —
Haskell, Swift), monomorphization (generate a specialized copy — Rust static dispatch), or
vtables at runtime (`dyn Trait`, Go interfaces).

**⚠️ Trait resolution is a solver, and solvers have performance and termination problems.**
Rust's trait system is expressive enough that resolution can loop or blow up exponentially.
**[VERSIONED]** rustc has been building a **next-generation trait solver** for years
precisely to fix long-standing soundness bugs, unblock features (implied bounds, negative
impls), and improve compile times; it reached production use in coherence checking and, as
of 2026, stabilization work continues alongside **Polonius** (the next-generation borrow
checker). The lesson for a language designer: **an expressive trait/instance-resolution
system is a Prolog interpreter in your compiler. Budget accordingly.**

### 4.5 Generics: monomorphize or erase?

**[CONTESTED, and one of the genuinely load-bearing decisions.]**

| | **Monomorphization** (C++, Rust) | **Erasure / dictionaries** (Java, Haskell, Swift) |
|---|---|---|
| Runtime cost | **Zero** — specialized code, inlinable | Indirection: boxing, vtables, dictionaries |
| Code size | **Explodes** — one copy per instantiation | One copy |
| Compile time | **Slow** — the dominant cost in large Rust and C++ builds | Fast |
| Separate compilation | Hard — need the generic body available | Clean |
| Reflection on type args | Available | Erased (Java's `List<T>` doesn't know `T` at runtime) |
| Error messages | Instantiation-time errors, often terrible (C++ templates pre-concepts) | Declaration-time errors |

Go's 1.18 generics chose a **middle path (GC shape stenciling)**: monomorphize by
*representation class* rather than by exact type, so all pointer-shaped types share one
instantiation. This bounds code growth while keeping most of the performance.

**[DURABLE] Whichever you choose, define errors at the *declaration* site.** C++ templates
famously deferred all checking to instantiation, producing the pathological error messages
that concepts (C++20) exist to fix. Rust's trait bounds check the generic body against its
bounds up front. This is worth real implementation effort.

### 4.6 Ownership, borrowing, and linearity

Rust's contribution is proving that **affine types plus region inference can eliminate
memory-safety bugs at compile time with no runtime cost**, in a language people actually
ship. The machinery:
- **Ownership**: each value has one owner; drop at scope end (RAII).
- **Borrowing**: `&T` (shared, many) / `&mut T` (unique, one). The XOR rule — aliasing xor
  mutation — is what makes the whole thing sound *and* is what makes it hard to learn.
- **Lifetimes**: regions inferred by the borrow checker; annotations only where inference
  can't decide.

**[VERSIONED] NLL (non-lexical lifetimes) shipped in 2018; Polonius** is the next-generation
formulation, designed to accept currently-rejected patterns (notably "lending iterators").
Rust's own 2026 project-goal updates describe an "alpha" Polonius being tested on CI
alongside the next-gen trait solver, with worst-case slowdowns still being tracked. **The
honest read: borrow checking is a research area with a shipped product on top of it, and
the shipped product's rules are still being refined eight years in.**

**Alternatives worth knowing**: linear types (must use exactly once — Linear Haskell),
uniqueness types (Clean), region/arena inference (MLKit, Cyclone — the direct ancestor of
Rust's design), and Swift's ARC with `~Copyable`/borrowing annotations retrofitted.

### 4.7 The other static analyses

These aren't "type checking" but live in the same phase and are equally load-bearing:
- **Exhaustiveness checking for pattern matching.** [DURABLE] **This is one of the highest
  value-per-implementation-effort features in language design.** Maranget's algorithm
  ("Warnings for pattern matching," 2007) is the standard reference and is genuinely
  implementable in a few hundred lines. It converts a whole class of runtime bugs into
  compile errors and it is what makes sum types pleasant instead of tedious.
- **Definite assignment** — is this variable initialized on every path?
- **Reachability / dead code**, **unused variables and imports**.
- **Effect checking** (§4.9).

### 4.8 Compile-time execution and metaprogramming

The spectrum, in increasing order of power and danger:
1. **Constant folding** — the compiler evaluates `2+2`.
2. **`constexpr`/`comptime`** — arbitrary evaluation at compile time (C++, **Zig's
   `comptime`**, which is also how Zig does generics).
3. **Hygienic macros** — syntax-to-syntax transforms that respect scope (Scheme, Rust).
4. **Procedural macros / compiler plugins** — arbitrary code running in the compiler.
5. **Full reflection** — programs inspecting and generating themselves.

**[VERSIONED, and a genuinely big deal] C++26 shipped static reflection**, which Herb
Sutter called "the biggest upgrade since templates" and "C++'s decade-defining rocket
engine." **The ISO committee completed technical work on C++26 on 28 March 2026** in
London; the headline features are **static reflection, contracts, `std::execution`
(sender/receiver), and a hardened standard library**. **GCC 16.1 (30 April 2026) already
ships reflection and contracts.** Note the syntax churn as a lesson: the reflection
operator changed from `^` to `^^` during standardization, so early adopter code needed
migration.

> **⚠️ GOTCHA — compile-time execution means your compiler contains an interpreter, and
> that interpreter is a security boundary and a performance cliff.** You need: a step
> limit (or programs won't terminate), determinism (or builds aren't reproducible), a
> decision about whether it can do I/O (**it should not**), and an answer for what it means
> to debug it. Zig's community discussions consistently name `comptime` as both its best
> feature and a significant pain point — that's the shape of this trade-off.

### 4.9 Effects

An active research frontier that is reaching production:
- **Checked exceptions** (Java) — the first mainstream effect system, and widely considered
  a partial failure because it lacked polymorphism: you couldn't write a higher-order
  function generic over what its argument throws.
- **Monadic effects** (Haskell) — expressive, composes badly (monad transformers).
- **Algebraic effects and handlers** (Koka, Eff, OCaml 5's effect handlers) — the current
  best answer. Effects are operations; handlers interpret them. This is what makes OCaml 5's
  concurrency work without colouring functions.
- **Function colouring** (§8.3 → `language-runtimes-interpreters-and-jits`): async/await is an *ad-hoc, unprincipled effect system*.
  This is the strongest argument for doing effects properly.
