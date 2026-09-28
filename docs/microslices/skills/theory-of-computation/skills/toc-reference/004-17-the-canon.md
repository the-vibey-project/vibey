---
id: skill-17-the-canon-9b3cddd875
purpose: 17 the canon
source: src/vibey_tools/skills/plugins/theory-of-computation/skills/toc-reference/SKILL.md
requires: ["skill-16-currency-snapshot-verified-august-2026-79175ff51c"]
links: ["skill-18-quick-reference-793df50c98"]
---

## §17. The Canon

### 17.1 Books

| Author | Work | Why |
|---|---|---|
| **Michael Sipser** | ***Introduction to the Theory of Computation*** | **The standard, and the best-written.** If you read one book, this is it |
| **Hopcroft, Motwani & Ullman** | *Introduction to Automata Theory, Languages, and Computation* | The classic reference; heavier |
| **Arora & Barak** | ***Computational Complexity: A Modern Approach*** (draft free online) | The graduate complexity text |
| **Garey & Johnson** | ***Computers and Intractability*** | 1979, still indispensable — **the catalogue of NP-complete problems you check your problem against** (§6.1 → `toc-computability-and-complexity`) |
| **Moore & Mertens** | *The Nature of Computation* | **The most enjoyable serious book in the field.** Deep and genuinely readable |
| **Cormen et al.** | *Introduction to Algorithms* (CLRS) | The algorithms companion; its NP-completeness chapter is a good entry point |
| **Aho, Lam, Sethi & Ullman** | *Compilers* ("the Dragon Book") | §3 → `toc-automata-regex-and-parsing` in full |
| **Pierce** | ***Types and Programming Languages*** (TAPL) | §12 → `toc-type-systems-and-randomization`, and the standard |
| **Harper** | *Practical Foundations for Programming Languages* | The rigorous alternative |
| **Nielson, Nielson & Hankin** | *Principles of Program Analysis* | Abstract interpretation and §4.1 → `toc-computability-and-complexity`'s trade-offs |
| **Lynch** | *Distributed Algorithms* | §11 → `toc-beyond-np-space-and-distributed-limits`, formally |
| **Kleinberg & Tardos** | *Algorithm Design* | The best treatment of *recognizing* NP-hardness in the wild |
| **Petzold** | *The Annotated Turing* | Turing's 1936 paper, explained line by line. A genuinely lovely way in |
| **Hofstadter** | *Gödel, Escher, Bach* | The famous one. Inspiring, not a textbook |

### 17.2 Courses and online
**MIT 6.045 / 18.404** (Sipser's own course, OCW), **Stanford CS103/CS154**,
**Berkeley CS172**, **Scott Aaronson's lecture notes and *Quantum Computing Since
Democritus***, and **the Complexity Zoo** (the catalogue of every complexity class anyone
has defined — genuinely useful and slightly absurd).

**Blogs and people**: **Scott Aaronson** (*Shtetl-Optimized* — the field's most reliable
public explainer and hype-check), **Lance Fortnow & Bill Gasarch** (*Computational
Complexity*), **Quanta Magazine** (the best popular coverage of results like §10 → `toc-beyond-np-space-and-distributed-limits`'s),
**Terence Tao**, **Ryan Williams**, **Virginia Vassilevska Williams** (fine-grained),
**Ian Mertz / James Cook** (catalytic computing), **Leslie Lamport** (TLA+ and §11 → `toc-beyond-np-space-and-distributed-limits`).

**Practical**: the **Z3 guide** and **cvc5 docs**, **TLA+ Video Course** (Lamport's own),
**Alloy** documentation, **SMT-LIB**, **regex101** and ReDoS analyzers, **Godbolt** for
seeing what your abstractions cost.

---
