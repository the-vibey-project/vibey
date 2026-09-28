---
id: skill-7-sat-smt-and-solvers-853b252172
purpose: 7 sat smt and solvers
source: src/vibey_tools/skills/plugins/theory-of-computation/skills/toc-computability-and-complexity/SKILL.md
requires: ["skill-6-your-problem-is-np-hard-now-what-26f15bc1fa"]
links: []
---

## §7. SAT, SMT, and Solvers

**[DURABLE] The single most useful practical lesson in complexity for working engineers:
NP-complete does not mean unsolvable, and there is mature, free tooling that will do it
for you.**

**SAT** — Boolean satisfiability. The first problem proved NP-complete (Cook–Levin), and
the one where the gap between theory and practice is widest. Modern **CDCL** solvers
(conflict-driven clause learning, with unit propagation, watched literals, restarts,
clause learning) have made SAT solving one of the great practical successes in CS — the
literature's own phrase for it is **"the unreasonable effectiveness of SAT solvers."**

**SMT** — SAT plus theories: integers and reals, bit-vectors, arrays, strings, algebraic
datatypes, uninterpreted functions. **This is what makes it useful for software**, because
your constraints aren't Boolean.

**[VERSIONED] The tools**: **Z3** (Microsoft — general-purpose, the default, especially
strong on quantifier-free arithmetic and arrays), **cvc5** (strings, algebraic datatypes,
advanced arithmetic), **Bitwuzla** (bit-vectors and floating point; successor to
Boolector), **Yices 2** (fast on linear arithmetic and bit-vectors), **MathSAT**
(interpolation, model generation), and **CaDiCaL**/**Kissat** on the pure-SAT side.
**MiniZinc/OR-Tools** for constraint programming; **Gurobi/CPLEX/HiGHS** for MIP.

**Where they're actually used**: **program verification** (Dafny, Verus, F\*, Viper,
Creusot, and the whole bounded-model-checking family), **symbolic execution** and test
generation, **type checking** for refinement types, **package dependency resolution**
(PubGrub and friends), **scheduling and configuration**, and **hardware verification**,
which is where the money was that built these tools.

> **⚠️ GOTCHA — the practical failure modes of solvers, which nobody warns you about:**
> - **Encoding dominates everything.** The same problem stated two ways can differ by
>   orders of magnitude. **Move as much of the problem outside the solver as you can** —
>   the solver is the scalability bottleneck, so preprocessing pays enormously.
> - **⚠️ Instability is real and under-appreciated.** Semantically identical queries can
>   flip between solved and timed-out based on trivial syntactic differences — variable
>   naming, term ordering, formula shape. Research on program-verification workloads has
>   measured this directly and built tooling specifically to normalize queries and
>   stabilize solve times. **If your CI intermittently fails a verification step, this may
>   be why, and it is not your logic being wrong.**
> - **Non-linear arithmetic is where solvers fall over**, and disabling the non-linear
>   solver is a known stabilization technique in production verification work.
> - **Always set a timeout and handle `unknown`.** `unknown` is a real answer, not an error.
> - **Solvers disagree**, and portfolio approaches (dispatch to whichever solver suits the
>   theory) are standard in serious tools for exactly that reason.
