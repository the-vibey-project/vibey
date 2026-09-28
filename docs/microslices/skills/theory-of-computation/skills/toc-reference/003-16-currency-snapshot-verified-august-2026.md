---
id: skill-16-currency-snapshot-verified-august-2026-79175ff51c
purpose: 16 currency snapshot verified august 2026
source: src/vibey_tools/skills/plugins/theory-of-computation/skills/toc-reference/SKILL.md
requires: ["skill-15-contested-questions-1ef970f6be"]
links: ["skill-17-the-canon-9b3cddd875"]
---

## §16. Currency Snapshot — verified August 2026

**[DURABLE] Read this section differently from the others in this collection.** Nearly
everything above has been settled for decades — automata theory (1950s–60s), computability
(1930s), NP-completeness (1971), FLP (1985), CAP (2000). **The correct expectation for
this domain is that it does not move**, and a currency section that claimed otherwise would
be misleading. Here is what actually changed.

| Thing | Status as of Aug 2026 | Decay risk |
|---|---|---|
| **⚠️ Williams' time–space simulation** | **February 2025: TIME[t] ⊆ SPACE[O(√(t log t))]** for multitape Turing machines (STOC 2025, ECCC TR25-017). **Replaces Hopcroft–Paul–Valiant's t/log t from 1975** — a near-quadratic improvement on a bound that stood 50 years. Proof reduces to **Tree Evaluation** and uses the **Cook–Mertz** algorithm from the catalytic-computing line. **⚠️ The simulation does not preserve the time bound.** Described as "an earthquake of a result"; genuine progress toward **P ≠ PSPACE** | Low (it's a theorem) |
| **What it opened** | Williams notes the result "opens up an entirely new set of questions that did not seem possible to ask," including whether a genuine **time–space tradeoff** simulation is achievable. **Active area** | Medium |
| **P vs NP** | **Open.** Still a Millennium Problem. Consensus remains P ≠ NP. Relativization, natural proofs, and algebrization barriers all stand | Very low |
| **Fine-grained complexity** | Mature and active. **SETH**, **OV**, **3SUM**, **APSP** remain the load-bearing conjectures. ⚠️ Note the **no-go results**: work has shown barriers against proving fine-grained complexity of certain problems (e.g. approximate CVP) via SETH/QSETH-style reductions — **the method has limits, and they're being mapped** | Medium |
| **Quantum fine-grained** | ⚠️ **SETH fails quantumly** — Grover solves CNF-SAT in ~2^(n/2) — so **QSETH** frameworks (Buhrman–Patro–Speelman; Aaronson–Chia–Lin–Wang–Zhang) exist to translate quantum query lower bounds into conditional quantum time lower bounds for BQP problems. Active through 2026, including SETH/QSETH-hardness results for local Hamiltonian ground-state energy estimation | Medium |
| **SAT/SMT solvers** | **Z3**, **cvc5** (v1.3.x era), **Bitwuzla**, **Yices 2**, **MathSAT**, **CaDiCaL 2.0** all actively maintained and competing at SMT-COMP/SAT Competition. **Portfolio dispatch across solvers is standard practice** in serious verification tools (ESBMC dispatches across five) | Medium |
| **⚠️ Solver instability** | A measured, published problem: semantically identical queries flip between solved and timed-out on syntactic perturbation. **Tooling now exists specifically to address it** — context-driven normalization reported improving stability to **>98% under 10 random mutations**, and earlier work reported mitigating instability by ~29% on Z3 and ~41% on cvc5. **Disabling non-linear arithmetic is a known stabilization technique** in production verification | Medium |
| **Verification tooling** | Dafny, Verus, F\*, Viper, Creusot, Prusti, Flux, GoBra and the BMC family (ESBMC, CBMC) are active. **LLM-assisted proof automation** is an active research direction | **High** |

**Goes stale fastest:** solver versions and verification tooling. **Essentially never
stale:** §1–§6 → `toc-automata-regex-and-parsing`, `toc-computability-and-complexity`, §8 → `toc-beyond-np-space-and-distributed-limits`, §11 → `toc-beyond-np-space-and-distributed-limits`, §12 → `toc-type-systems-and-randomization`'s fundamentals, §14 — these are theorems.

---
