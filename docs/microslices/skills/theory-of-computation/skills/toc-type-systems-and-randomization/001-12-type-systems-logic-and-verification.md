---
id: skill-12-type-systems-logic-and-verification-4d5ccab59a
purpose: 12 type systems logic and verification
source: src/vibey_tools/skills/plugins/theory-of-computation/skills/toc-type-systems-and-randomization/SKILL.md
requires: []
links: ["skill-13-randomness-approximation-and-heuristics-139de28a6c"]
---

## §12. Type Systems, Logic, and Verification

**[DURABLE] Type systems are decidable approximations of undecidable properties** (§4.1 → `toc-computability-and-complexity`) —
which is the single most clarifying sentence about them.

**The Curry–Howard correspondence**: **propositions are types; proofs are programs.**
Proving a theorem and writing a well-typed program are the same activity. This is not a
cute analogy — it's the foundation of **Coq/Rocq, Lean, Agda, Idris**, and the reason
dependent types let you encode "this list has length n" or "this index is in bounds" in the
type itself.

**The expressiveness ladder, and its cost:**
```
Simply typed          decidable, restrictive
+ polymorphism        Hindley–Milner: full inference, decidable, the ML/Haskell sweet spot
+ subtyping           inference gets harder
+ higher-rank         ⚠️ full inference becomes undecidable — you must annotate
+ dependent types     type checking decidable, inference generally not.
                      Types can express arbitrary properties — and you now write proofs
```
**⚠️ The trade-off is fundamental and not fixable**: more expressive types catch more bugs
and demand more annotation. **A type system that inferred everything and caught everything
would decide undecidable properties.**

**Practical verification** (see §7 → `toc-computability-and-complexity` for the solvers underneath): **model checking** —
exhaustively explore a finite state space, with **⚠️ state-space explosion** as the
permanent enemy, mitigated by symbolic representation, abstraction, and partial-order
reduction. **Abstract interpretation** — sound over-approximation, accepting false
positives to guarantee no false negatives (this is where sound static analyzers live).
**TLA+ / Alloy** — specify and check designs before building them, and **[DURABLE] this is
the highest-leverage formal method for most engineers** because it catches design errors
in distributed protocols where testing cannot.

**[DURABLE] The pragmatic position**: full functional verification is expensive and
justified for kernels, compilers, cryptography, and safety-critical control. **Lightweight
formal methods — property-based testing, model checking a protocol, a TLA+ spec of your
consensus design — have a far better cost/benefit ratio and are radically under-used.**

---
