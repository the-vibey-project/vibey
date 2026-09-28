---
id: skill-16-contested-questions-09580a9a30
purpose: 16 contested questions
source: src/vibey_tools/skills/plugins/programming-language-development/skills/language-development-reference/SKILL.md
requires: ["skill-15-anti-patterns-c5d6743c0f"]
links: ["skill-17-currency-snapshot-verified-august-2026-195d089bbe"]
---

## §16. Contested Questions

**16.1 Static vs. dynamic typing.** The empirical literature is genuinely weaker than
advocates on both sides claim — controlled studies are small, short, and use toy tasks.
What is well-supported: static types help *at scale*, on *large teams*, over *long
maintenance periods*, and enable tooling (completion, refactoring) that dynamic languages
approximate at best. Gradual typing (TypeScript, mypy, Sorbet) is the market's revealed
preference, which is itself informative.

**16.2 Monomorphization vs. erasure.** §4.5 → `language-design-parsing-and-types`. Runtime speed vs. compile time and code size.

**16.3 GC vs. ownership.** Rust proved ownership is viable in a mainstream language; it also
proved it has a real learning-curve cost. GC is easier to use and rules out whole domains
(hard real-time, kernel, tiny embedded). Neither wins; the domain decides.

**16.4 async/await vs. green threads.** §8.3 → `language-runtimes-interpreters-and-jits`. Function colouring vs. runtime requirement.

**16.5 LLVM or not.** §7.1 → `language-irs-optimization-and-backends`. Best-in-class codegen and target coverage vs. compile speed,
dependency weight, and API churn. Zig is running the "not" experiment in public; rustc is
running the "both" experiment. Note that Cranelift's ~20% codegen speedup yields only ~5%
total build speedup in rustc — **the backend is often not the bottleneck people assume**.

**16.6 Safe C++ vs. Profiles.** WG21 rejected borrow checking for C++ and chose the
Profiles direction; the enforcement attribute then slipped to C++29. *For Profiles*:
incremental, no rewrite, works on existing code. *Against*: many practitioners consider it
unable to deliver the guarantees borrow checking does. **C++26 did ship real safety
improvements you get by recompiling** — hardened standard library plus contracts — so this
is not nothing; whether it's sufficient is exactly the disputed point.

**16.7 Sea of nodes.** Powerful reordering vs. debuggability. V8 moving parts of TurboFan
away from it is evidence that the debuggability cost is real at scale.

**16.8 Batteries-included standard library.** §13 → `language-diagnostics-tooling-and-evolution`.

**16.9 Formal verification's cost/benefit.** CompCert's Csmith result is the strongest
pro-verification evidence in the field; the counter is that CompCert optimizes less and
took enormous effort. Translation validation (Alive2) is the compromise most projects
should actually adopt.

**16.10 How much syntax novelty is justified?** §1.3 → `language-design-parsing-and-types`. Familiarity is worth a great deal;
occasionally a genuinely better notation (Rust's `?`, pattern matching, pipelines) earns
its cost. The failure mode is novelty *for its own sake*.

---
