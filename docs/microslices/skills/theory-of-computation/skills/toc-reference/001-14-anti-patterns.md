---
id: skill-14-anti-patterns-9c567e5762
purpose: 14 anti patterns
source: src/vibey_tools/skills/plugins/theory-of-computation/skills/toc-reference/SKILL.md
requires: []
links: ["skill-15-contested-questions-1ef970f6be"]
---

## §14. Anti-Patterns

| Anti-pattern | Why |
|---|---|
| Parsing nested structures with regex | **Regular can't do context-free.** A theorem, not a skill issue (§2.2 → `toc-automata-regex-and-parsing`) |
| Backtracking regex on untrusted input | **ReDoS.** Use a linear-time engine (§2.3 → `toc-automata-regex-and-parsing`) |
| Nested quantifiers over overlapping alternations | The catastrophic-backtracking shape |
| Building regexes from user input | Injection with extra steps |
| Hand-rolling a parser for JSON/YAML/CSV | The edge cases have eaten more time than almost anything |
| Boolean flags instead of an explicit state machine | Silently reaches states nobody enumerated (§1.2 → `toc-automata-regex-and-parsing`) |
| Demanding a static analyzer with no false positives | **You are asking for a halting-problem solver** (§4.1 → `toc-computability-and-complexity`) |
| "The compiler is wrong, this code is fine" | Type systems reject some correct programs **by construction** (§12 → `toc-type-systems-and-randomization`) |
| Giving up because a problem is NP-hard | Solvers handle industrial instances routinely (§6.3 → `toc-computability-and-complexity`, §7 → `toc-computability-and-complexity`) |
| Assuming NP-hard is fine because tests passed | **Test data is structured; production isn't.** Timeout + fallback (§6.3 → `toc-computability-and-complexity`) |
| Treating "optimal" as a requirement nobody stated | Often the highest-value question to ask (§6.2 → `toc-computability-and-complexity`) |
| Optimizing a quadratic string-diff | **Conditionally optimal under SETH.** Change the problem (§9 → `toc-beyond-np-space-and-distributed-limits`) |
| Assuming polynomial means fast | O(n¹⁰⁰) is polynomial (§5.2 → `toc-computability-and-complexity`) |
| Comparing asymptotics without measuring | Constants and cache dominate at real n |
| Quoting worst case as the expected case | Quicksort and simplex are the standing counterexamples |
| Throwing a problem at a solver without thinking about encoding | **Encoding dominates solver performance** (§7 → `toc-computability-and-complexity`) |
| Treating an SMT `unknown` or timeout as a logic bug | ⚠️ **Solver instability is measured and real** (§7 → `toc-computability-and-complexity`) |
| Claiming deterministic asynchronous consensus | **FLP says no.** Every real protocol adds an assumption (§11 → `toc-beyond-np-space-and-distributed-limits`) |
| Promising exactly-once delivery | **Two Generals.** At-least-once + idempotency (§11 → `toc-beyond-np-space-and-distributed-limits`) |
| Citing CAP outside a partition | It's about partition behaviour. Use PACELC (§11 → `toc-beyond-np-space-and-distributed-limits`) |
| "Eventually consistent" as a specification | Name the model (§11 → `toc-beyond-np-space-and-distributed-limits`) |
| Assuming reliable/ordered delivery or synced clocks without saying so | You picked a side of a theorem by accident (§11 → `toc-beyond-np-space-and-distributed-limits`) |
| Believing a barrier is permanent because it's old | **A 50-year-old space bound fell in 2025** (§10 → `toc-beyond-np-space-and-distributed-limits`, §16) |

---
